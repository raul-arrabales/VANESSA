from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from ..services.agent_engine_client import (
    AgentEngineClientError,
    create_execution as _create_execution,
    get_execution as _get_execution,
)
from ..services.platform_runtime import get_active_platform_runtime_for_dispatch
from ..services.platform_service import get_active_platform_runtime as _get_active_platform_runtime
from ..services.runtime_profile_service import resolve_runtime_profile as _resolve_runtime_profile


class ExecutionManagementRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def build_request_id(
    header_value: str | None,
    *,
    uuid_factory: Callable[[], str] = lambda: str(uuid4()),
) -> str:
    normalized = str(header_value or "").strip()
    return normalized or uuid_factory()


def is_transport_failure(exc: AgentEngineClientError) -> bool:
    if exc.code in {"agent_engine_unreachable", "EXEC_TIMEOUT"}:
        return True
    return int(exc.status_code) in {502, 503, 504}


def fallback_unavailable_payload(*, request_id: str, operation: str) -> dict[str, object]:
    return {
        "error": "EXEC_UPSTREAM_UNAVAILABLE",
        "message": "Agent execution service is temporarily unavailable",
        "details": {
            "operation": operation,
            "fallback_applied": True,
            "request_id": request_id,
        },
    }


def create_agent_execution_response(
    database_url: str,
    *,
    config,
    payload: Any,
    request_id: str,
    requested_by_user_id: int,
    requested_by_role: str,
    fallback_enabled: bool | None = None,
    create_execution_fn: Callable[..., tuple[dict[str, Any], int]] = _create_execution,
    get_active_platform_runtime_fn: Callable[..., dict[str, Any]] = _get_active_platform_runtime,
    resolve_runtime_profile_fn: Callable[[str], str] = _resolve_runtime_profile,
) -> tuple[dict[str, Any], int]:
    if not config.agent_execution_via_engine:
        raise ExecutionManagementRequestError(
            status_code=503,
            code="agent_execution_disabled",
            message="Agent execution via engine is disabled",
        )

    if not isinstance(payload, dict):
        raise ExecutionManagementRequestError(
            status_code=400,
            code="invalid_payload",
            message="Expected JSON object",
        )

    agent_id = str(payload.get("agent_id", "")).strip()
    execution_input = payload.get("input")
    if not agent_id:
        raise ExecutionManagementRequestError(
            status_code=400,
            code="invalid_agent_id",
            message="agent_id is required",
        )
    if execution_input is not None and not isinstance(execution_input, dict):
        raise ExecutionManagementRequestError(
            status_code=400,
            code="invalid_input",
            message="input must be an object when provided",
        )

    org_id = str(payload.get("org_id", "")).strip() or None
    group_id = str(payload.get("group_id", "")).strip() or None
    platform_runtime = get_active_platform_runtime_for_dispatch(
        database_url,
        config,
        get_active_platform_runtime_fn=get_active_platform_runtime_fn,
    )

    try:
        return create_execution_fn(
            base_url=config.agent_engine_url.rstrip("/"),
            service_token=config.agent_engine_service_token,
            request_id=request_id,
            agent_id=agent_id,
            execution_input=execution_input if isinstance(execution_input, dict) else {},
            requested_by_user_id=requested_by_user_id,
            requested_by_role=requested_by_role,
            runtime_profile=resolve_runtime_profile_fn(database_url),
            platform_runtime=platform_runtime,
            org_id=org_id,
            group_id=group_id,
        )
    except AgentEngineClientError as exc:
        if bool(config.agent_execution_fallback if fallback_enabled is None else fallback_enabled) and is_transport_failure(exc):
            return fallback_unavailable_payload(
                request_id=request_id,
                operation="create_execution",
            ), 503
        return {
            "error": exc.code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        }, exc.status_code


def get_agent_execution_response(
    config,
    *,
    execution_id: str,
    request_id: str,
    fallback_enabled: bool | None = None,
    get_execution_fn: Callable[..., tuple[dict[str, Any], int]] = _get_execution,
) -> tuple[dict[str, Any], int]:
    normalized_execution_id = str(execution_id).strip()
    if not normalized_execution_id:
        raise ExecutionManagementRequestError(
            status_code=400,
            code="invalid_execution_id",
            message="execution_id is required",
        )

    try:
        return get_execution_fn(
            base_url=config.agent_engine_url.rstrip("/"),
            service_token=config.agent_engine_service_token,
            request_id=request_id,
            execution_id=normalized_execution_id,
        )
    except AgentEngineClientError as exc:
        if bool(config.agent_execution_fallback if fallback_enabled is None else fallback_enabled) and is_transport_failure(exc):
            return fallback_unavailable_payload(
                request_id=request_id,
                operation="get_execution",
            ), 503
        return {
            "error": exc.code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        }, exc.status_code
