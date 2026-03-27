from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ...application.execution_management_service import (
    ExecutionManagementRequestError,
    build_request_id,
    create_agent_execution_response,
    get_agent_execution_response,
)
from ...authz import require_role
from ...config import get_auth_config
from ...services.agent_engine_client import create_execution as _create_execution
from ...services.agent_engine_client import get_execution as _get_execution
from ...services.platform_service import get_active_platform_runtime as _get_active_platform_runtime
from ...services.platform_types import PlatformControlPlaneError
from ...services.runtime_profile_service import resolve_runtime_profile as _resolve_runtime_profile

bp = Blueprint("executions", __name__)

create_execution = _create_execution
get_execution = _get_execution
get_active_platform_runtime = _get_active_platform_runtime
resolve_runtime_profile = _resolve_runtime_profile


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _config():
    return get_auth_config()


def _database_url() -> str:
    return _config().database_url


def _fallback_enabled() -> bool:
    return bool(_config().agent_execution_fallback)


def _request_id() -> str:
    return build_request_id(request.headers.get("X-Request-Id"))


@bp.post("/v1/agent-executions")
@require_role("user")
def create_agent_execution_route():
    try:
        payload, status_code = create_agent_execution_response(
            _database_url(),
            config=_config(),
            payload=request.get_json(silent=True),
            request_id=_request_id(),
            requested_by_user_id=int(g.current_user["id"]),
            requested_by_role=str(g.current_user.get("role", "user")),
            fallback_enabled=_fallback_enabled(),
            create_execution_fn=create_execution,
            get_active_platform_runtime_fn=get_active_platform_runtime,
            resolve_runtime_profile_fn=resolve_runtime_profile,
        )
    except ExecutionManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    except PlatformControlPlaneError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)

    return jsonify(payload), status_code


@bp.get("/v1/agent-executions/<execution_id>")
@require_role("user")
def get_agent_execution_route(execution_id: str):
    try:
        payload, status_code = get_agent_execution_response(
            _config(),
            execution_id=execution_id,
            request_id=_request_id(),
            fallback_enabled=_fallback_enabled(),
            get_execution_fn=get_execution,
        )
    except ExecutionManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)

    return jsonify(payload), status_code


__all__ = [
    "bp",
    "_config",
    "_database_url",
    "_json_error",
    "_fallback_enabled",
    "_request_id",
    "create_execution",
    "get_execution",
    "get_active_platform_runtime",
    "resolve_runtime_profile",
]
