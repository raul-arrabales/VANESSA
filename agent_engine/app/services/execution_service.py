from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..repositories import executions as executions_repo
from ..schemas.agent_executions import AgentExecutionRecord
from .policy_runtime_gate import (
    ExecutionBlockedError,
    require_agent_execute_permission,
    resolve_agent_spec,
    resolve_runtime_profile,
    validate_runtime_and_dependencies,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def _simulate_execution_result(*, agent_id: str, runtime_profile: str, execution_input: dict[str, Any]) -> dict[str, Any]:
    simulate_error = str(execution_input.get("simulate_error", "")).strip().lower()
    if simulate_error == "timeout":
        raise ExecutionBlockedError(code="EXEC_TIMEOUT", message="Execution timed out", status_code=504)
    if simulate_error == "upstream_unavailable":
        raise ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message="Upstream LLM/tool dependency unavailable",
            status_code=503,
        )
    if simulate_error == "internal":
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500)

    prompt = str(execution_input.get("prompt", "")).strip()
    output_text = (
        f"Agent '{agent_id}' executed in {runtime_profile} profile"
        if not prompt
        else f"Agent '{agent_id}' executed in {runtime_profile} profile with prompt: {prompt}"
    )
    return {
        "output_text": output_text,
        "tool_calls": [],
        "model_calls": [],
    }


def _build_execution(
    *,
    execution_id: str,
    status: str,
    agent_ref: str,
    agent_version: str,
    model_ref: str | None,
    runtime_profile: str,
    created_at: str,
    started_at: str | None,
    finished_at: str | None,
    result: dict[str, Any] | None,
    error: dict[str, Any] | None,
) -> AgentExecutionRecord:
    return AgentExecutionRecord(
        id=execution_id,
        status=status,
        agent_ref=agent_ref,
        agent_version=agent_version,
        model_ref=model_ref,
        runtime_profile=runtime_profile,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        result=result,
        error=error,
    )


def create_execution(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    agent_id = str(payload.get("agent_id", "")).strip()
    if not agent_id:
        raise ValueError("invalid_agent_id")

    execution_input = payload.get("input")
    if execution_input is not None and not isinstance(execution_input, dict):
        raise ValueError("invalid_input")
    normalized_input = execution_input if isinstance(execution_input, dict) else {}

    requested_by_user_id = int(payload.get("requested_by_user_id", 0) or 0)
    requested_by_role = str(payload.get("requested_by_role", "user")).strip().lower() or "user"
    runtime_profile = resolve_runtime_profile(payload.get("runtime_profile"))

    execution_id = str(uuid4())
    created_at = _iso_now()
    queued = _build_execution(
        execution_id=execution_id,
        status="queued",
        agent_ref=agent_id,
        agent_version="v1",
        model_ref=None,
        runtime_profile=runtime_profile,
        created_at=created_at,
        started_at=None,
        finished_at=None,
        result=None,
        error=None,
    )
    executions_repo.save_execution(
        queued,
        requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
        input_payload=normalized_input,
    )

    try:
        agent_entity = resolve_agent_spec(agent_id=agent_id)
        require_agent_execute_permission(
            user_id=requested_by_user_id,
            user_role=requested_by_role,
            agent_id=agent_id,
        )
        agent_version, model_ref = validate_runtime_and_dependencies(
            agent_entity=agent_entity,
            runtime_profile=runtime_profile,
        )
        running_started_at = _iso_now()
        running = _build_execution(
            execution_id=execution_id,
            status="running",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=model_ref,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=running_started_at,
            finished_at=None,
            result=None,
            error=None,
        )
        executions_repo.save_execution(
            running,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        result = _simulate_execution_result(
            agent_id=agent_id,
            runtime_profile=runtime_profile,
            execution_input=normalized_input,
        )
        finished = _build_execution(
            execution_id=execution_id,
            status="succeeded",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=model_ref,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=running_started_at,
            finished_at=_iso_now(),
            result=result,
            error=None,
        )
        executions_repo.save_execution(
            finished,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        return {"execution": finished.to_payload()}, 201
    except ExecutionBlockedError as exc:
        blocked_status = "blocked" if exc.status_code in {403} else "failed"
        failed_execution = _build_execution(
            execution_id=execution_id,
            status=blocked_status,
            agent_ref=agent_id,
            agent_version="v1",
            model_ref=None,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=None,
            finished_at=_iso_now(),
            result=None,
            error=_error_payload(exc.code, exc.message, exc.details),
        )
        executions_repo.save_execution(
            failed_execution,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        raise
    except Exception as exc:
        failed_execution = _build_execution(
            execution_id=execution_id,
            status="failed",
            agent_ref=agent_id,
            agent_version="v1",
            model_ref=None,
            runtime_profile=runtime_profile,
            created_at=created_at,
            started_at=None,
            finished_at=_iso_now(),
            result=None,
            error=_error_payload("EXEC_INTERNAL_ERROR", str(exc)),
        )
        executions_repo.save_execution(
            failed_execution,
            requested_by_user_id=requested_by_user_id if requested_by_user_id > 0 else None,
            input_payload=normalized_input,
        )
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
        ) from exc


def get_execution(execution_id: str) -> tuple[dict[str, Any], int]:
    normalized_id = execution_id.strip()
    if not normalized_id:
        raise ValueError("invalid_execution_id")
    execution = executions_repo.get_execution(normalized_id)
    if execution is None:
        raise ExecutionBlockedError(
            code="execution_not_found",
            message="Execution not found",
            status_code=404,
        )
    return {"execution": execution.to_payload()}, 200

