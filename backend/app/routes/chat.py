from __future__ import annotations

from json import dumps
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request, stream_with_context

from ..authz import require_role
from ..config import get_auth_config
from ..services.agent_engine_client import AgentEngineClientError
from ..services.chat_conversations import (
    CHAT_CONVERSATION_UNSET,
    ChatConversationInferenceError,
    ChatConversationNotFoundError,
    ChatConversationValidationError,
    create_plain_conversation,
    delete_plain_conversation,
    get_plain_conversation_detail,
    list_plain_conversations,
    send_plain_message,
    stream_plain_message,
    update_plain_conversation,
)
from ..services.knowledge_chat_service import map_knowledge_chat_engine_error, run_knowledge_chat

bp = Blueprint("chat", __name__)


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _request_id() -> str:
    header_value = request.headers.get("X-Request-Id", "").strip()
    return header_value or str(uuid4())


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _format_sse_event(event_name: str, payload: dict[str, object]) -> str:
    return f"event: {event_name}\ndata: {dumps(payload)}\n\n"


@bp.get("/v1/chat/conversations")
@require_role("user")
def list_conversations_route():
    payload = list_plain_conversations(
        _database_url(),
        owner_user_id=int(g.current_user["id"]),
    )
    return jsonify({"conversations": payload}), 200


@bp.post("/v1/chat/conversations")
@require_role("user")
def create_conversation_route():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    conversation = create_plain_conversation(
        _database_url(),
        owner_user_id=int(g.current_user["id"]),
        model_id=payload.get("model_id"),
    )
    return jsonify({"conversation": conversation}), 201


@bp.get("/v1/chat/conversations/<conversation_id>")
@require_role("user")
def get_conversation_route(conversation_id: str):
    try:
        conversation = get_plain_conversation_detail(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            conversation_id=conversation_id,
        )
    except ChatConversationNotFoundError:
        return _json_error(404, "conversation_not_found", "Conversation not found")

    return jsonify({"conversation": conversation}), 200


@bp.patch("/v1/chat/conversations/<conversation_id>")
@require_role("user")
def update_conversation_route(conversation_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    has_title = "title" in payload
    has_model_id = "model_id" in payload
    if not has_title and not has_model_id:
        return _json_error(400, "invalid_payload", "title or model_id is required")

    try:
        conversation = update_plain_conversation(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            conversation_id=conversation_id,
            title=payload["title"] if has_title else CHAT_CONVERSATION_UNSET,
            model_id=payload["model_id"] if has_model_id else CHAT_CONVERSATION_UNSET,
        )
    except ChatConversationValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except ChatConversationNotFoundError:
        return _json_error(404, "conversation_not_found", "Conversation not found")

    return jsonify({"conversation": conversation}), 200


@bp.delete("/v1/chat/conversations/<conversation_id>")
@require_role("user")
def delete_conversation_route(conversation_id: str):
    try:
        delete_plain_conversation(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            conversation_id=conversation_id,
        )
    except ChatConversationNotFoundError:
        return _json_error(404, "conversation_not_found", "Conversation not found")

    return jsonify({"deleted": True}), 200


@bp.post("/v1/chat/conversations/<conversation_id>/messages")
@require_role("user")
def post_conversation_message_route(conversation_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        response_payload = send_plain_message(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            conversation_id=conversation_id,
            prompt=payload.get("prompt"),
        )
    except ChatConversationValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except ChatConversationNotFoundError:
        return _json_error(404, "conversation_not_found", "Conversation not found")
    except ChatConversationInferenceError as exc:
        return jsonify(exc.payload), exc.status_code

    return jsonify(response_payload), 200


@bp.post("/v1/chat/conversations/<conversation_id>/messages/stream")
@require_role("user")
def post_conversation_message_stream_route(conversation_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    try:
        stream = stream_plain_message(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            conversation_id=conversation_id,
            prompt=payload.get("prompt"),
        )
    except ChatConversationValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except ChatConversationNotFoundError:
        return _json_error(404, "conversation_not_found", "Conversation not found")
    except ChatConversationInferenceError as exc:
        return jsonify(exc.payload), exc.status_code

    def _response_stream():
        for event in stream:
            yield _format_sse_event(str(event["event"]), dict(event["data"]))

    return Response(
        stream_with_context(_response_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.post("/v1/chat/knowledge")
@require_role("user")
def knowledge_chat_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_payload", "message": "Expected JSON object"}), 400

    try:
        response_payload, status_code = run_knowledge_chat(
            database_url=_database_url(),
            config=_config(),
            request_id=_request_id(),
            prompt=payload.get("prompt", ""),
            requested_model_id=payload.get("model", ""),
            history_payload=payload.get("history", []),
        )
    except AgentEngineClientError as exc:
        error_payload, error_status = map_knowledge_chat_engine_error(exc)
        return jsonify(error_payload), error_status
    except Exception as exc:  # pragma: no cover - guarded by route behavior tests
        current_app.logger.exception("Knowledge chat request failed: %s", exc)
        return jsonify({
            "error": "knowledge_chat_failed",
            "message": "Knowledge chat request failed.",
        }), 500

    return jsonify(response_payload), status_code
