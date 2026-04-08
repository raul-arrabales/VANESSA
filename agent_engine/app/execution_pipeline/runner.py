from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..policies.runtime_policy import (
    require_agent_execute_permission_stage as require_agent_execute_permission,
    resolve_agent_spec_stage as resolve_agent_spec,
    resolve_agent_tools_stage as resolve_agent_tools,
    validate_runtime_and_dependencies_stage as validate_runtime_and_dependencies,
)
from ..repositories import executions as executions_repo
from ..retrieval.options import normalize_retrieval_request
from ..retrieval.runtime import (
    coerce_execution_messages,
    execute_retrieval_call,
    prepend_retrieval_context,
)
from ..schemas.agent_executions import AgentExecutionRecord
from ..services.policy_runtime_gate import ExecutionBlockedError, resolve_runtime_profile
from ..services.runtime_client import (
    EmbeddingsRuntimeClientError,
    LlmRuntimeClientError,
    build_llm_runtime_client,
)
from ..tool_runtime.dispatch import (
    build_tool_definition,
    invoke_tool_call,
    resolve_tool_runtime_binding,
    runtime_capability_for_transport,
    tool_message_content,
)
from .types import ConversationState, ExecutionContext, ExecutionResult

_MAX_TOOL_CALL_ROUNDS = 3


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


def _deterministic_execution_result(*, agent_id: str, runtime_profile: str) -> ExecutionResult:
    return ExecutionResult(
        output_text=f"Agent '{agent_id}' executed in {runtime_profile} profile",
    )


def _execute_model_call(
    *,
    context: ExecutionContext,
    model_ref: str | None,
    agent_tools: list[dict[str, Any]],
) -> tuple[ExecutionResult, str | None]:
    _raise_simulated_error_if_requested(context.execution_input)
    messages = list(context.conversation.messages)
    if not messages and context.conversation.retrieval_request is None:
        return _deterministic_execution_result(agent_id=context.agent_id, runtime_profile=context.runtime_profile), model_ref

    embedding_call, retrieval_call, retrieval_results = execute_retrieval_call(
        retrieval_request=context.conversation.retrieval_request,
        platform_runtime=context.platform_runtime,
    )
    effective_messages = prepend_retrieval_context(messages, retrieval_results=retrieval_results)

    runtime_snapshot = context.platform_runtime if isinstance(context.platform_runtime, dict) else {}
    requested_model_override = str(context.execution_input.get("model", "")).strip() or None
    effective_requested_model = requested_model_override or model_ref
    tool_lookup: dict[str, dict[str, Any]] = {}
    tool_definitions: list[dict[str, Any]] = []
    for tool_entity in agent_tools:
        tool_spec = tool_entity.get("current_spec") if isinstance(tool_entity.get("current_spec"), dict) else {}
        tool_name = str(tool_spec.get("tool_name", "")).strip()
        if not tool_name:
            continue
        runtime_capability = runtime_capability_for_transport(str(tool_spec.get("transport", "")))
        resolve_tool_runtime_binding(platform_runtime=runtime_snapshot, capability_key=runtime_capability)
        tool_lookup[tool_name] = tool_entity
        tool_definitions.append(build_tool_definition(tool_entity))

    model_calls: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    try:
        client = build_llm_runtime_client(runtime_snapshot)
    except LlmRuntimeClientError as exc:
        if exc.code == "runtime_timeout":
            raise ExecutionBlockedError(code="EXEC_TIMEOUT", message="Execution timed out", status_code=504, details=exc.details) from exc
        if exc.code in {"runtime_unreachable", "runtime_upstream_unavailable"}:
            raise ExecutionBlockedError(code="EXEC_UPSTREAM_UNAVAILABLE", message="Upstream LLM/tool dependency unavailable", status_code=503, details=exc.details) from exc
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500, details=exc.details) from exc

    llm_binding = runtime_snapshot.get("capabilities", {}).get("llm_inference", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    effective_model = effective_requested_model
    completion: dict[str, Any] | None = None
    for _round_index in range(_MAX_TOOL_CALL_ROUNDS):
        try:
            completion = client.chat_completion(
                requested_model=effective_requested_model,
                messages=effective_messages,
                tools=tool_definitions or None,
            )
        except LlmRuntimeClientError as exc:
            if exc.code == "runtime_timeout":
                raise ExecutionBlockedError(code="EXEC_TIMEOUT", message="Execution timed out", status_code=504, details=exc.details) from exc
            if exc.code in {"runtime_unreachable", "runtime_upstream_unavailable"}:
                raise ExecutionBlockedError(code="EXEC_UPSTREAM_UNAVAILABLE", message="Upstream LLM/tool dependency unavailable", status_code=503, details=exc.details) from exc
            raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500, details=exc.details) from exc
        effective_model = str(completion.get("requested_model", "")).strip() or effective_requested_model
        model_calls.append(
            {
                "provider_slug": llm_binding.get("slug"),
                "provider_key": llm_binding.get("provider_key"),
                "deployment_profile_slug": deployment_profile.get("slug"),
                "requested_model": effective_model,
                "status_code": int(completion.get("status_code", 200) or 200),
            }
        )
        completion_tool_calls = completion.get("tool_calls") if isinstance(completion.get("tool_calls"), list) else []
        if not completion_tool_calls:
            break

        effective_messages.append({"role": "assistant", "content": [], "tool_calls": completion_tool_calls})
        for tool_call in completion_tool_calls:
            tool_name = str(((tool_call.get("function") or {}).get("name", ""))).strip()
            tool_entity = tool_lookup.get(tool_name)
            if tool_entity is None:
                raise ExecutionBlockedError(
                    code="EXEC_TOOL_NOT_ALLOWED",
                    message=f"Tool '{tool_name}' referenced by the model is not allowed",
                    status_code=403,
                )
            call_record, tool_payload = invoke_tool_call(
                tool_entity=tool_entity,
                tool_call=tool_call,
                platform_runtime=runtime_snapshot,
            )
            tool_calls.append(call_record)
            effective_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(tool_call.get("id", "")).strip(),
                    "content": tool_message_content(tool_payload),
                }
            )
    else:
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
            details={"reason": "tool_round_limit_exceeded"},
        )

    if completion is None:
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500)

    return (
        ExecutionResult(
            output_text=str(completion.get("output_text", "")),
            tool_calls=tool_calls,
            embedding_calls=[embedding_call] if embedding_call is not None else [],
            model_calls=model_calls,
            retrieval_calls=[retrieval_call] if retrieval_call is not None else [],
        ),
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
    normalized_retrieval = normalize_retrieval_request(normalized_input)
    normalized_messages = coerce_execution_messages(normalized_input)
    if normalized_retrieval is not None and not normalized_messages:
        raise ValueError("invalid_retrieval_input")
    platform_runtime = payload.get("platform_runtime")

    requested_by_user_id = int(payload.get("requested_by_user_id", 0) or 0)
    requested_by_role = str(payload.get("requested_by_role", "user")).strip().lower() or "user"
    runtime_profile = resolve_runtime_profile(payload.get("runtime_profile"))

    execution_id = str(uuid4())
    created_at = _iso_now()
    conversation = ConversationState(messages=normalized_messages, retrieval_request=normalized_retrieval)
    context = ExecutionContext(
        execution_id=execution_id,
        agent_id=agent_id,
        runtime_profile=runtime_profile,
        requested_by_user_id=requested_by_user_id,
        requested_by_role=requested_by_role,
        execution_input=normalized_input,
        platform_runtime=platform_runtime if isinstance(platform_runtime, dict) else None,
        conversation=conversation,
    )
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
        agent_tools = resolve_agent_tools(agent_entity=agent_entity, runtime_profile=runtime_profile)
        requested_model_override = str(normalized_input.get("model", "")).strip() or None
        running_model_ref = requested_model_override or model_ref
        running_started_at = _iso_now()
        running = _build_execution(
            execution_id=execution_id,
            status="running",
            agent_ref=agent_id,
            agent_version=agent_version,
            model_ref=running_model_ref,
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
            context=context,
            model_ref=model_ref,
            agent_tools=agent_tools,
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
            result=result.to_payload(),
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
