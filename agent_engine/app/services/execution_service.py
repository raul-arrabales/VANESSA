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
from .runtime_client import LlmRuntimeClientError, build_llm_runtime_client


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def _raise_simulated_error_if_requested(execution_input: dict[str, Any]) -> None:
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


def _deterministic_execution_result(*, agent_id: str, runtime_profile: str) -> dict[str, Any]:
    output_text = f"Agent '{agent_id}' executed in {runtime_profile} profile"
    return {
        "output_text": output_text,
        "tool_calls": [],
        "model_calls": [],
    }


def _coerce_execution_messages(execution_input: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages = execution_input.get("messages")
    if isinstance(raw_messages, list):
        normalized = _coerce_messages(raw_messages)
        if normalized:
            return normalized

    prompt = str(execution_input.get("prompt", "")).strip()
    if prompt:
        return [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    return []


def _coerce_messages(messages: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        content = item.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                normalized.append({"role": role, "content": [{"type": "text", "text": text}]})
            continue
        if not isinstance(content, list):
            continue
        parts: list[dict[str, str]] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if str(part.get("type", "")).strip().lower() != "text":
                continue
            text = str(part.get("text", "")).strip()
            if text:
                parts.append({"type": "text", "text": text})
        if parts:
            normalized.append({"role": role, "content": parts})
    return normalized


def _execute_model_call(
    *,
    execution_input: dict[str, Any],
    agent_id: str,
    runtime_profile: str,
    model_ref: str | None,
    platform_runtime: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    _raise_simulated_error_if_requested(execution_input)
    messages = _coerce_execution_messages(execution_input)
    if not messages:
        return _deterministic_execution_result(agent_id=agent_id, runtime_profile=runtime_profile), model_ref

    runtime_snapshot = platform_runtime if isinstance(platform_runtime, dict) else {}
    try:
        client = build_llm_runtime_client(runtime_snapshot)
        completion = client.chat_completion(
            requested_model=model_ref,
            messages=messages,
        )
    except LlmRuntimeClientError as exc:
        if exc.code == "runtime_timeout":
            raise ExecutionBlockedError(
                code="EXEC_TIMEOUT",
                message="Execution timed out",
                status_code=504,
                details=exc.details,
            ) from exc
        if exc.code in {"runtime_unreachable", "runtime_upstream_unavailable"}:
            raise ExecutionBlockedError(
                code="EXEC_UPSTREAM_UNAVAILABLE",
                message="Upstream LLM/tool dependency unavailable",
                status_code=503,
                details=exc.details,
            ) from exc
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
            details=exc.details,
        ) from exc

    llm_binding = runtime_snapshot.get("capabilities", {}).get("llm_inference", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    effective_model = str(completion.get("requested_model", "")).strip() or model_ref
    return (
        {
            "output_text": str(completion.get("output_text", "")),
            "tool_calls": [],
            "model_calls": [
                {
                    "provider_slug": llm_binding.get("slug"),
                    "provider_key": llm_binding.get("provider_key"),
                    "deployment_profile_slug": deployment_profile.get("slug"),
                    "requested_model": effective_model,
                    "status_code": int(completion.get("status_code", 200) or 200),
                }
            ],
        },
        effective_model,
    )


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
    platform_runtime = payload.get("platform_runtime")

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
        result, effective_model_ref = _execute_model_call(
            execution_input=normalized_input,
            agent_id=agent_id,
            runtime_profile=runtime_profile,
            model_ref=model_ref,
            platform_runtime=platform_runtime if isinstance(platform_runtime, dict) else None,
        )
        finished = _build_execution(
            execution_id=execution_id,
            status="succeeded",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=effective_model_ref,
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
