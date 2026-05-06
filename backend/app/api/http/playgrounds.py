from __future__ import annotations

from json import dumps
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request, send_file, stream_with_context

from ...application.playgrounds_service import (
    PlaygroundChatExecutionError,
    PlaygroundSessionNotFoundError,
    PlaygroundSessionValidationError,
    create_playground_session,
    delete_playground_session,
    get_playground_knowledge_base_options,
    get_playground_model_options,
    get_playground_options,
    get_playground_session_detail,
    list_playground_sessions,
    send_playground_message,
    send_temporary_playground_message,
    stream_playground_message,
    stream_temporary_playground_message,
    update_playground_session,
)
from ...authz import require_role
from ...config import get_auth_config
from ...services.agent_engine_client import AgentEngineClientError
from ...services.knowledge_source_files import resolve_knowledge_source_file
from ...services.platform_types import PlatformControlPlaneError

bp = Blueprint("playgrounds", __name__)


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


@bp.get("/v1/playgrounds/sessions")
@require_role("user")
def list_playground_sessions_route():
    playground_kind = request.args.get("playground_kind")
    try:
        payload = list_playground_sessions(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            playground_kind=playground_kind,
        )
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    return jsonify({"sessions": payload}), 200


@bp.post("/v1/playgrounds/sessions")
@require_role("user")
def create_playground_session_route():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        session = create_playground_session(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            payload=payload,
        )
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    return jsonify({"session": session}), 201


@bp.get("/v1/playgrounds/sessions/<session_id>")
@require_role("user")
def get_playground_session_route(session_id: str):
    try:
        session = get_playground_session_detail(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            session_id=session_id,
            playground_kind=request.args.get("playground_kind"),
        )
    except PlaygroundSessionNotFoundError:
        return _json_error(404, "session_not_found", "Playground session not found")
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    return jsonify({"session": session}), 200


@bp.patch("/v1/playgrounds/sessions/<session_id>")
@require_role("user")
def update_playground_session_route(session_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        session = update_playground_session(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            session_id=session_id,
            payload=payload,
        )
    except PlaygroundSessionNotFoundError:
        return _json_error(404, "session_not_found", "Playground session not found")
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    return jsonify({"session": session}), 200


@bp.delete("/v1/playgrounds/sessions/<session_id>")
@require_role("user")
def delete_playground_session_route(session_id: str):
    try:
        delete_playground_session(
            _database_url(),
            owner_user_id=int(g.current_user["id"]),
            session_id=session_id,
        )
    except PlaygroundSessionNotFoundError:
        return _json_error(404, "session_not_found", "Playground session not found")
    return jsonify({"deleted": True}), 200


@bp.post("/v1/playgrounds/sessions/<session_id>/messages")
@require_role("user")
def post_playground_message_route(session_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        response_payload = send_playground_message(
            _database_url(),
            config=_config(),
            request_id=_request_id(),
            owner_user_id=int(g.current_user["id"]),
            owner_role=str(g.current_user.get("role", "user")),
            session_id=session_id,
            prompt=payload.get("prompt"),
        )
    except PlaygroundSessionNotFoundError:
        return _json_error(404, "session_not_found", "Playground session not found")
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except PlaygroundChatExecutionError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return jsonify({"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc))}), exc.status_code
    except AgentEngineClientError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code
    except Exception as exc:  # pragma: no cover
        current_app.logger.exception("Playground message request failed: %s", exc)
        return _json_error(500, "playground_message_failed", "Playground message request failed.")
    return jsonify(response_payload), 200


@bp.post("/v1/playgrounds/temporary/messages")
@require_role("user")
def post_temporary_playground_message_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        response_payload = send_temporary_playground_message(
            _database_url(),
            config=_config(),
            request_id=_request_id(),
            owner_user_id=int(g.current_user["id"]),
            owner_role=str(g.current_user.get("role", "user")),
            payload=payload,
        )
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except PlaygroundChatExecutionError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return jsonify({"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc))}), exc.status_code
    except AgentEngineClientError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code
    except Exception as exc:  # pragma: no cover
        current_app.logger.exception("Temporary playground message request failed: %s", exc)
        return _json_error(500, "playground_message_failed", "Playground message request failed.")
    return jsonify(response_payload), 200


@bp.post("/v1/playgrounds/sessions/<session_id>/messages/stream")
@require_role("user")
def post_playground_message_stream_route(session_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        stream = stream_playground_message(
            _database_url(),
            config=_config(),
            request_id=_request_id(),
            owner_user_id=int(g.current_user["id"]),
            owner_role=str(g.current_user.get("role", "user")),
            session_id=session_id,
            prompt=payload.get("prompt"),
        )
    except PlaygroundSessionNotFoundError:
        return _json_error(404, "session_not_found", "Playground session not found")
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except PlaygroundChatExecutionError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return jsonify({"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc))}), exc.status_code
    except AgentEngineClientError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code

    def _response_stream():
        try:
            for event in stream:
                yield _format_sse_event(str(event["event"]), dict(event["data"]))
        except AgentEngineClientError as exc:
            yield _format_sse_event("error", {"error": exc.code, "message": exc.message, "status_code": exc.status_code})
        except PlaygroundChatExecutionError as exc:
            payload = exc.payload if isinstance(exc.payload, dict) else {}
            yield _format_sse_event(
                "error",
                {"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc)), "status_code": exc.status_code},
            )

    return Response(
        stream_with_context(_response_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.post("/v1/playgrounds/temporary/messages/stream")
@require_role("user")
def post_temporary_playground_message_stream_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        stream = stream_temporary_playground_message(
            _database_url(),
            config=_config(),
            request_id=_request_id(),
            owner_user_id=int(g.current_user["id"]),
            owner_role=str(g.current_user.get("role", "user")),
            payload=payload,
        )
    except PlaygroundSessionValidationError as exc:
        return _json_error(400, exc.code, exc.message)
    except PlaygroundChatExecutionError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        return jsonify({"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc))}), exc.status_code
    except AgentEngineClientError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code

    def _response_stream():
        try:
            for event in stream:
                yield _format_sse_event(str(event["event"]), dict(event["data"]))
        except AgentEngineClientError as exc:
            yield _format_sse_event("error", {"error": exc.code, "message": exc.message, "status_code": exc.status_code})
        except PlaygroundChatExecutionError as exc:
            payload = exc.payload if isinstance(exc.payload, dict) else {}
            yield _format_sse_event(
                "error",
                {"error": payload.get("error", "playground_chat_failed"), "message": payload.get("message", str(exc)), "status_code": exc.status_code},
            )

    return Response(
        stream_with_context(_response_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.get("/v1/playgrounds/options")
@require_role("user")
def get_playground_options_route():
    payload = get_playground_options(
        _database_url(),
        config=_config(),
        actor_user_id=int(g.current_user["id"]),
        actor_role=str(g.current_user.get("role", "user")),
    )
    return jsonify(payload), 200


@bp.get("/v1/playgrounds/model-options")
@require_role("user")
def get_playground_model_options_route():
    payload = get_playground_model_options(
        _database_url(),
        config=_config(),
        actor_user_id=int(g.current_user["id"]),
        actor_role=str(g.current_user.get("role", "user")),
        playground_kind=request.args.get("playground_kind"),
    )
    return jsonify(payload), 200


@bp.get("/v1/playgrounds/knowledge-base-options")
@require_role("user")
def get_playground_knowledge_base_options_route():
    payload = get_playground_knowledge_base_options(
        _database_url(),
        config=_config(),
    )
    return jsonify(payload), 200


@bp.get("/v1/playgrounds/knowledge-bases/<knowledge_base_id>/documents/<document_id>/source-file")
@require_role("user")
def get_playground_knowledge_source_file_route(knowledge_base_id: str, document_id: str):
    try:
        source_file = resolve_knowledge_source_file(
            _database_url(),
            config=_config(),
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
        )
    except PlatformControlPlaneError as exc:
        return jsonify({"error": exc.code, "message": exc.message, "details": exc.details}), exc.status_code
    return send_file(
        source_file.path,
        mimetype=source_file.mimetype,
        as_attachment=source_file.as_attachment,
        download_name=source_file.download_name,
        conditional=True,
    )
