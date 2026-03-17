from __future__ import annotations

from uuid import uuid4

from flask import Blueprint, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..services.agent_engine_client import AgentEngineClientError
from ..services.knowledge_chat_service import map_knowledge_chat_engine_error, run_knowledge_chat

bp = Blueprint("chat", __name__)


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _request_id() -> str:
    header_value = request.headers.get("X-Request-Id", "").strip()
    return header_value or str(uuid4())


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

    return jsonify(response_payload), status_code
