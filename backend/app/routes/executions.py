from __future__ import annotations

from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..services.agent_engine_client import (
    AgentEngineClientError,
    create_execution,
    get_execution,
)
from ..services.runtime_profile_service import resolve_runtime_profile

bp = Blueprint("executions", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return _config().database_url


def _config():
    return get_auth_config()


def _agent_engine_url() -> str:
    return _config().agent_engine_url.rstrip("/")


def _agent_engine_service_token() -> str:
    return _config().agent_engine_service_token


def _request_id() -> str:
    header_value = request.headers.get("X-Request-Id", "").strip()
    return header_value or str(uuid4())


def _fallback_enabled() -> bool:
    return bool(_config().agent_execution_fallback)


def _is_transport_failure(exc: AgentEngineClientError) -> bool:
    if exc.code in {"agent_engine_unreachable", "EXEC_TIMEOUT"}:
        return True
    return int(exc.status_code) in {502, 503, 504}


def _fallback_unavailable_response(*, request_id: str, operation: str):
    return (
        jsonify(
            {
                "error": "EXEC_UPSTREAM_UNAVAILABLE",
                "message": "Agent execution service is temporarily unavailable",
                "details": {
                    "operation": operation,
                    "fallback_applied": True,
                    "request_id": request_id,
                },
            }
        ),
        503,
    )


@bp.post("/v1/agent-executions")
@require_role("user")
def create_agent_execution():
    if not _config().agent_execution_via_engine:
        return _json_error(503, "agent_execution_disabled", "Agent execution via engine is disabled")

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    agent_id = str(payload.get("agent_id", "")).strip()
    execution_input = payload.get("input")
    if not agent_id:
        return _json_error(400, "invalid_agent_id", "agent_id is required")
    if execution_input is not None and not isinstance(execution_input, dict):
        return _json_error(400, "invalid_input", "input must be an object when provided")

    org_id = str(payload.get("org_id", "")).strip() or None
    group_id = str(payload.get("group_id", "")).strip() or None

    request_id = _request_id()
    try:
        response_payload, status_code = create_execution(
            base_url=_agent_engine_url(),
            service_token=_agent_engine_service_token(),
            request_id=request_id,
            agent_id=agent_id,
            execution_input=execution_input if isinstance(execution_input, dict) else {},
            requested_by_user_id=int(g.current_user["id"]),
            requested_by_role=str(g.current_user.get("role", "user")),
            runtime_profile=resolve_runtime_profile(_database_url()),
            org_id=org_id,
            group_id=group_id,
        )
    except AgentEngineClientError as exc:
        if _fallback_enabled() and _is_transport_failure(exc):
            return _fallback_unavailable_response(
                request_id=request_id,
                operation="create_execution",
            )
        if exc.status_code >= 500:
            return _json_error(exc.status_code, exc.code, exc.message)
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code

    return jsonify(response_payload), status_code


@bp.get("/v1/agent-executions/<execution_id>")
@require_role("user")
def get_agent_execution(execution_id: str):
    if not execution_id.strip():
        return _json_error(400, "invalid_execution_id", "execution_id is required")

    request_id = _request_id()
    try:
        response_payload, status_code = get_execution(
            base_url=_agent_engine_url(),
            service_token=_agent_engine_service_token(),
            request_id=request_id,
            execution_id=execution_id.strip(),
        )
    except AgentEngineClientError as exc:
        if _fallback_enabled() and _is_transport_failure(exc):
            return _fallback_unavailable_response(
                request_id=request_id,
                operation="get_execution",
            )
        if exc.status_code >= 500:
            return _json_error(exc.status_code, exc.code, exc.message)
        return jsonify({"error": exc.code, "message": exc.message}), exc.status_code

    return jsonify(response_payload), status_code
