from __future__ import annotations

from datetime import datetime, timezone
from json import dumps, loads
from queue import Queue
from threading import Thread
from typing import Any, Iterator
from uuid import uuid4

from vanessa_shared.workflow_prompt_contract import normalize_agent_runtime_prompts

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
    effective_tool_spec,
    runtime_capability_for_tool_spec,
    tool_message_content,
)
from .model_streaming import DeltaEmitter, model_status_details, stream_model_completion
from .progress import ProgressRecorder, compact_payload, summarize_results, trim_text
from .types import ConversationState, ExecutionContext, ExecutionResult

_MAX_TOOL_CALL_ROUNDS = 3
_MAX_WORKFLOW_ACTION_ITERATIONS = 5


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


def _system_text_message(text: str) -> dict[str, Any]:
    return {"role": "system", "content": [{"type": "text", "text": text}]}


def _tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    raw_arguments = str(((tool_call.get("function") or {}).get("arguments", "")))
    if not raw_arguments.strip():
        return {}
    try:
        parsed = loads(raw_arguments)
    except ValueError:
        return {"raw_arguments": trim_text(raw_arguments)}
    return parsed if isinstance(parsed, dict) else {"value": compact_payload(parsed)}


def _tool_status_label(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "web_search":
        query = trim_text(arguments.get("query"), limit=140)
        return f"Searching the web for: {query}" if query else "Searching the web"
    return f"Running tool: {tool_name}" if tool_name else "Running tool"


def _agent_current_spec(agent_entity: dict[str, Any]) -> dict[str, Any]:
    current_spec = agent_entity.get("current_spec")
    return current_spec if isinstance(current_spec, dict) else {}


def _prepend_agent_instructions(messages: list[dict[str, Any]], *, agent_spec: dict[str, Any]) -> list[dict[str, Any]]:
    instructions = str(agent_spec.get("instructions") or "").strip()
    if not instructions:
        return messages
    return [_system_text_message(instructions), *messages]


def _agent_retrieval_instructions(agent_spec: dict[str, Any]) -> str | None:
    runtime_prompts = normalize_agent_runtime_prompts(
        agent_spec.get("runtime_prompts"),
        agent_type=agent_spec.get("agent_type"),
    )
    retrieval_context = str(runtime_prompts.get("retrieval_context") or "").strip()
    return retrieval_context or None


def _agent_type(agent_spec: dict[str, Any]) -> str:
    return str(agent_spec.get("agent_type") or "react").strip().lower() or "react"


def _workflow_actions(agent_spec: dict[str, Any]) -> list[dict[str, Any]]:
    workflow_definition = agent_spec.get("workflow_definition") if isinstance(agent_spec.get("workflow_definition"), dict) else {}
    raw_actions = workflow_definition.get("actions") if isinstance(workflow_definition.get("actions"), list) else []
    if raw_actions:
        return [item for item in raw_actions if isinstance(item, dict)]
    raw_steps = workflow_definition.get("steps") if isinstance(workflow_definition.get("steps"), list) else []
    actions: list[dict[str, Any]] = []
    for index, step in enumerate(raw_steps):
        if not isinstance(step, dict):
            continue
        actions.append({
            "id": str(step.get("id") or f"mcp_tool_{index + 1}"),
            "type": "mcp_tool",
            "name": str(step.get("name") or step.get("exposed_tool_name") or f"MCP tool {index + 1}"),
            "mcp_server_slug": str(step.get("mcp_server_slug") or ""),
            "exposed_tool_name": str(step.get("exposed_tool_name") or ""),
            "input_bindings": {},
            "static_arguments": step.get("arguments") if isinstance(step.get("arguments"), dict) else {},
            "output_variables": [{"name": f"step_{index + 1}_output", "label": "Step output", "type": "text"}],
        })
    return actions


def _tool_entity_lookup(agent_tools: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for tool_entity in agent_tools:
        tool_spec = effective_tool_spec(tool_entity)
        slug = str(tool_spec.get("slug") or "").strip()
        if slug:
            lookup[slug] = tool_entity
    return lookup


def _workflow_step_result_text(result: dict[str, Any]) -> str:
    for key in ("output_text", "answer", "summary", "message", "result"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return compact_payload(result)


def _workflow_state_from_input(execution_input: dict[str, Any]) -> dict[str, Any]:
    state = execution_input.get("workflow_state")
    if not isinstance(state, dict) or str(state.get("status") or "") == "completed":
        state = {}
    return {
        "version": 2,
        "action_index": int(state.get("action_index", 0) or 0) if isinstance(state, dict) else 0,
        "variables": dict(state.get("variables") or {}) if isinstance(state.get("variables"), dict) else {},
        "action_outputs": dict(state.get("action_outputs") or {}) if isinstance(state.get("action_outputs"), dict) else {},
        "status": str(state.get("status") or "running") if isinstance(state, dict) else "running",
    }


def _message_text(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "message")
        content = message.get("content")
        if isinstance(content, list):
            text = " ".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
        else:
            text = str(content or "")
        if text.strip():
            lines.append(f"{role}: {text.strip()}")
    return "\n".join(lines)


def _parse_json_object(text: Any) -> dict[str, Any]:
    try:
        parsed = loads(str(text or "").strip())
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _llm_json(
    *,
    context: ExecutionContext,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    system_prompt: str,
    user_prompt: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    client = build_llm_runtime_client(runtime_snapshot)
    completion = client.chat_completion(
        requested_model=requested_model,
        messages=[
            _system_text_message(system_prompt),
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ],
    )
    output_text = str(completion.get("output_text") or "").strip()
    return _parse_json_object(output_text), {
        "requested_model": str(completion.get("requested_model") or requested_model or ""),
        "status_code": int(completion.get("status_code", 200) or 200),
    }, output_text


def _llm_text(
    *,
    context: ExecutionContext,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, dict[str, Any] | None]:
    client = build_llm_runtime_client(runtime_snapshot)
    completion = client.chat_completion(
        requested_model=requested_model,
        messages=[
            _system_text_message(system_prompt),
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ],
    )
    return str(completion.get("output_text") or "").strip(), {
        "requested_model": str(completion.get("requested_model") or requested_model or ""),
        "status_code": int(completion.get("status_code", 200) or 200),
    }


def _workflow_json_with_repair(
    *,
    context: ExecutionContext,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    system_prompt: str,
    initial_user_prompt: str,
    repair_system_prompt: str,
    repair_user_prompt: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    model_calls: list[dict[str, Any]] = []
    parsed: dict[str, Any] = {}
    raw_output = ""
    try:
        parsed, model_call, raw_output = _llm_json(
            context=context,
            runtime_snapshot=runtime_snapshot,
            requested_model=requested_model,
            system_prompt=system_prompt,
            user_prompt=initial_user_prompt,
        )
        if model_call:
            model_calls.append(model_call)
    except LlmRuntimeClientError:
        parsed = {}

    if parsed:
        return parsed, model_calls, raw_output
    if not raw_output:
        return parsed, model_calls, raw_output

    try:
        repaired, model_call, _ = _llm_json(
            context=context,
            runtime_snapshot=runtime_snapshot,
            requested_model=requested_model,
            system_prompt=repair_system_prompt,
            user_prompt=f"{repair_user_prompt}\n\nPrevious model output to normalize:\n{raw_output}",
        )
        if model_call:
            model_calls.append(model_call)
        return repaired, model_calls, raw_output
    except LlmRuntimeClientError:
        return parsed, model_calls, raw_output


def _workflow_extract_variables_with_repair(
    *,
    context: ExecutionContext,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    action_prompt: str,
    variable_context: list[dict[str, Any]],
    state: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parsed, model_calls, _ = _workflow_json_with_repair(
        context=context,
        runtime_snapshot=runtime_snapshot,
        requested_model=requested_model,
        system_prompt=action_prompt,
        initial_user_prompt=(
            "Inspect the conversation and populate the declared workflow variables.\n"
            "Return only JSON with complete:boolean, variables:object, missing:array, response:string.\n\n"
            f"{_workflow_reference_guidance()}\n\n"
            f"Conversation:\n{_message_text(context.conversation.messages)}\n\n"
            f"Required workflow variables:\n{dumps(variable_context)}\n\n"
            f"Existing variables:\n{dumps(state['variables'])}"
        ),
        repair_system_prompt=(
            "You extract workflow state from a conversation.\n"
            "Return only valid JSON with complete:boolean, variables:object, missing:array, response:string.\n"
            "Do not write conversational prose outside the JSON object."
        ),
        repair_user_prompt=(
            f"Workflow action prompt:\n{action_prompt}\n\n"
            f"{_workflow_reference_guidance()}\n\n"
            f"Conversation:\n{_message_text(context.conversation.messages)}\n\n"
            f"Required workflow variables:\n{dumps(variable_context)}\n\n"
            f"Existing variables:\n{dumps(state['variables'])}"
        ),
    )
    return parsed, model_calls


def _workflow_compose_output_with_repair(
    *,
    context: ExecutionContext,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    action_prompt: str,
    selected_variables: list[dict[str, Any]],
    selected_values: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    parsed, model_calls, raw_output = _workflow_json_with_repair(
        context=context,
        runtime_snapshot=runtime_snapshot,
        requested_model=requested_model,
        system_prompt=action_prompt,
        initial_user_prompt=(
            "Compose the final workflow chat response.\n"
            "Return only JSON with response:string, complete:boolean.\n\n"
            f"{_workflow_reference_guidance()}\n\n"
            f"Workflow variable context:\n{dumps(selected_variables)}\n\n"
            f"Variables: {dumps(selected_values)}\n"
            f"Conversation:\n{_message_text(context.conversation.messages)}"
        ),
        repair_system_prompt=(
            "You compose final workflow chat responses.\n"
            "Return only valid JSON with response:string, complete:boolean.\n"
            "Do not write conversational prose outside the JSON object."
        ),
        repair_user_prompt=(
            f"Workflow action prompt:\n{action_prompt}\n\n"
            f"{_workflow_reference_guidance()}\n\n"
            f"Workflow variable context:\n{dumps(selected_variables)}\n\n"
            f"Variables: {dumps(selected_values)}\n"
            f"Conversation:\n{_message_text(context.conversation.messages)}"
        ),
    )
    response = str(parsed.get("response") or "").strip()
    if response:
        return response, model_calls
    if raw_output.strip():
        return raw_output.strip(), model_calls
    return "", model_calls


def _get_path(payload: Any, path: str) -> Any:
    if not path:
        return payload
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return None
    return current


def _store_output_variables(state: dict[str, Any], action: dict[str, Any], tool_payload: Any) -> None:
    variables = state.setdefault("variables", {})
    for variable in action.get("output_variables", []):
        if not isinstance(variable, dict):
            continue
        name = str(variable.get("name") or "").strip()
        if not name:
            continue
        extracted = _get_path(tool_payload, str(variable.get("path") or "").strip())
        variables[name] = extracted if isinstance(extracted, str) else compact_payload(extracted)


def _workflow_variable_context(
    *,
    variables: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    state_variables = state.get("variables") if isinstance(state.get("variables"), dict) else {}
    context: list[dict[str, Any]] = []
    for variable in variables:
        if not isinstance(variable, dict):
            continue
        name = str(variable.get("name") or "").strip()
        if not name:
            continue
        payload = {
            "name": name,
            "type": str(variable.get("type") or "text").strip() or "text",
            "label": str(variable.get("label") or name).strip() or name,
            "required": bool(variable.get("required", True)),
        }
        guidance = str(variable.get("guidance") or "").strip()
        if guidance:
            payload["guidance"] = guidance
        if name in state_variables:
            payload["value"] = state_variables.get(name)
        context.append(payload)
    return context


def _workflow_reference_guidance() -> str:
    return "\n".join(
        [
            "Workflow variable reference syntax:",
            "- Treat tokens such as {{user_name}} as references to workflow variables by name.",
            "- Use the structured workflow variable context below as the source of truth for names, types, labels, guidance, and current values.",
        ]
    )


def _workflow_available_variables(actions: list[dict[str, Any]], *, before_index: int) -> list[dict[str, Any]]:
    variables: list[dict[str, Any]] = []
    for action in actions[:before_index]:
        action_type = str(action.get("type") or "").strip()
        if action_type == "get_user_input":
            variables.extend([dict(variable) for variable in action.get("variables", []) if isinstance(variable, dict)])
        elif action_type == "mcp_tool":
            variables.extend([dict(variable) for variable in action.get("output_variables", []) if isinstance(variable, dict)])
    return variables


def _workflow_status_details(
    *,
    state: dict[str, Any],
    action_index: int,
    action: dict[str, Any],
    workflow_status: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = {
        "workflow_action_index": action_index,
        "workflow_action_name": str(action.get("name") or action.get("type") or f"action_{action_index + 1}"),
        "workflow_status": workflow_status,
        "workflow_variables": compact_payload(state.get("variables") if isinstance(state.get("variables"), dict) else {}),
    }
    if extra:
        details.update(extra)
    return details


def _workflow_action_prompt(action: dict[str, Any]) -> str:
    return str(action.get("prompt") or "").strip()


def _start_workflow_status(
    *,
    progress: ProgressRecorder,
    kind: str,
    label: str,
    state: dict[str, Any],
    action_index: int,
    action: dict[str, Any],
    workflow_status: str,
    extra: dict[str, Any] | None = None,
) -> str:
    return progress.start(
        kind=kind,
        label=label,
        details=_workflow_status_details(
            state=state,
            action_index=action_index,
            action=action,
            workflow_status=workflow_status,
            extra=extra,
        ),
    )


def _complete_workflow_status(
    *,
    progress: ProgressRecorder,
    status_id: str,
    kind: str,
    label: str,
    state: dict[str, Any],
    action_index: int,
    action: dict[str, Any],
    workflow_status: str,
    summary: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    progress.complete(
        status_id,
        kind=kind,
        label=label,
        summary=summary,
        details=_workflow_status_details(
            state=state,
            action_index=action_index,
            action=action,
            workflow_status=workflow_status,
            extra=extra,
        ),
    )


def _execute_workflow_agent(
    *,
    context: ExecutionContext,
    agent_entity: dict[str, Any],
    agent_tools: list[dict[str, Any]],
    progress: ProgressRecorder | None = None,
) -> tuple[ExecutionResult, str | None]:
    progress = progress or ProgressRecorder()
    agent_spec = _agent_current_spec(agent_entity)
    actions = _workflow_actions(agent_spec)
    if not actions:
        raise ExecutionBlockedError(
            code="EXEC_INVALID_AGENT",
            message="Workflow agent is missing workflow actions",
            status_code=422,
        )
    tool_lookup = _tool_entity_lookup(agent_tools)
    runtime_snapshot = context.platform_runtime if isinstance(context.platform_runtime, dict) else {}
    agent_domain = str(agent_spec.get("agent_domain") or "default").strip() or "default"
    requested_model = str(context.execution_input.get("model") or agent_spec.get("default_model_ref") or "").strip() or None
    state = _workflow_state_from_input(context.execution_input)
    tool_calls: list[dict[str, Any]] = []
    model_calls: list[dict[str, Any]] = []
    action_index = max(0, min(int(state.get("action_index", 0) or 0), len(actions)))
    while action_index < len(actions):
        action = actions[action_index]
        action_type = str(action.get("type") or "")
        action_prompt = _workflow_action_prompt(action)
        if not action_prompt:
            raise ExecutionBlockedError(
                code="EXEC_INVALID_AGENT",
                message=f"Workflow action {action_index + 1} is missing a prompt",
                status_code=422,
            )
        if action_type == "get_user_input":
            variables = [item for item in action.get("variables", []) if isinstance(item, dict)]
            variable_context = _workflow_variable_context(variables=variables, state=state)
            missing = [str(item.get("name") or "") for item in variables if not state["variables"].get(str(item.get("name") or ""))]
            status_id = _start_workflow_status(
                progress=progress,
                kind="thinking",
                label=f"Inspecting workflow input {action_index + 1}",
                state=state,
                action_index=action_index + 1,
                action=action,
                workflow_status="running",
            )
            parsed: dict[str, Any] = {}
            if missing:
                try:
                    parsed, extraction_model_calls = _workflow_extract_variables_with_repair(
                        context=context,
                        runtime_snapshot=runtime_snapshot,
                        requested_model=requested_model,
                        action_prompt=action_prompt,
                        variable_context=variable_context,
                        state=state,
                    )
                    model_calls.extend(extraction_model_calls)
                except LlmRuntimeClientError:
                    parsed = {}
                for name, value in (parsed.get("variables") if isinstance(parsed.get("variables"), dict) else {}).items():
                    if str(name) in missing and str(value).strip():
                        state["variables"][str(name)] = str(value).strip()
                missing = [str(item.get("name") or "") for item in variables if not state["variables"].get(str(item.get("name") or ""))]
            if missing:
                question = str(parsed.get("response") or parsed.get("question") or "").strip()
                if not question:
                    labels = [str(item.get("label") or item.get("name") or "").strip() for item in variables if str(item.get("name") or "") in missing]
                    try:
                        generated_question, model_call = _llm_text(
                            context=context,
                            runtime_snapshot=runtime_snapshot,
                            requested_model=requested_model,
                            system_prompt=action_prompt,
                            user_prompt=(
                                "Write the next assistant message for the user.\n"
                                "Ask only for the missing workflow information in natural language.\n"
                                "Do not mention prompts, JSON, variables, or placeholder tokens.\n"
                                "If placeholder syntax like {{user_name}} appears in the instructions, translate it into ordinary user-facing language.\n\n"
                                f"Missing variables: {dumps(missing)}\n"
                                f"Required workflow variables:\n{dumps(variable_context)}\n\n"
                                f"Existing variables:\n{dumps(state['variables'])}\n\n"
                                f"Conversation:\n{_message_text(context.conversation.messages)}"
                            ),
                        )
                        if model_call:
                            model_calls.append(model_call)
                        question = generated_question
                    except LlmRuntimeClientError:
                        question = ""
                    if not question:
                        question = (
                            "Please provide: " + ", ".join(labels)
                            if labels
                            else "Please provide the required information."
                        )
                state.update({"action_index": action_index, "status": "awaiting_user_input"})
                _complete_workflow_status(
                    progress=progress,
                    status_id=status_id,
                    kind="thinking",
                    label="Workflow is awaiting user input",
                    state=state,
                    action_index=action_index + 1,
                    action=action,
                    workflow_status="awaiting_user_input",
                    extra={"missing": missing},
                )
                return ExecutionResult(
                    output_text=question,
                    tool_calls=tool_calls,
                    model_calls=model_calls,
                    workflow_state=state,
                    workflow_status="awaiting_user_input",
                ), requested_model
            _complete_workflow_status(
                progress=progress,
                status_id=status_id,
                kind="thinking",
                label=f"Collected workflow input {action_index + 1}",
                state=state,
                action_index=action_index + 1,
                action=action,
                workflow_status="running",
            )
            action_index += 1
            state["action_index"] = action_index
            state["status"] = "running"
            continue

        if action_type == "mcp_tool":
            slug = str(action.get("mcp_server_slug") or "").strip()
            tool_entity = tool_lookup.get(slug)
            if tool_entity is None:
                raise ExecutionBlockedError(
                    code="EXEC_TOOL_NOT_ALLOWED",
                    message=f"Workflow action references unavailable MCP server '{slug}'",
                    status_code=403,
                )
            tool_spec = effective_tool_spec(tool_entity)
            tool_name = str(action.get("exposed_tool_name") or tool_spec.get("exposed_tool_name") or "").strip()
            runtime_capability = runtime_capability_for_tool_spec(tool_spec)
            resolve_tool_runtime_binding(platform_runtime=runtime_snapshot, capability_key=runtime_capability)
            input_bindings = action.get("input_bindings") if isinstance(action.get("input_bindings"), dict) else {}
            available_variables = _workflow_available_variables(actions, before_index=action_index)
            input_variables = _workflow_variable_context(
                variables=available_variables,
                state=state,
            )
            action_completed = False
            for iteration in range(1, _MAX_WORKFLOW_ACTION_ITERATIONS + 1):
                bound_values = {
                    field: state["variables"].get(str(binding.get("variable") or ""))
                    for field, binding in input_bindings.items()
                    if isinstance(binding, dict)
                }
                try:
                    parsed, model_call, _ = _llm_json(
                        context=context,
                        runtime_snapshot=runtime_snapshot,
                        requested_model=requested_model,
                        system_prompt=action_prompt,
                        user_prompt=(
                            "Create tool arguments for this workflow action.\n"
                            "Return only JSON with arguments:object, complete:boolean, variables:object, follow_up_message:string.\n\n"
                            f"Current workflow action name: {str(action.get('name') or tool_name or slug)}\n"
                            f"Tool name: {tool_name}\n"
                            f"{_workflow_reference_guidance()}\n\n"
                            f"Input schema: {dumps(tool_spec.get('input_schema') or {})}\n"
                            f"Workflow variable context:\n{dumps(input_variables)}\n\n"
                            f"Selected variables:\n{dumps(bound_values)}"
                        ),
                    )
                    if model_call:
                        model_calls.append(model_call)
                except LlmRuntimeClientError:
                    parsed = {}
                arguments = parsed.get("arguments") if isinstance(parsed.get("arguments"), dict) else bound_values
                status_id = _start_workflow_status(
                    progress=progress,
                    kind="running_tool",
                    label=f"Running workflow action {action_index + 1}: {str(action.get('name') or tool_name or slug)}",
                    state=state,
                    action_index=action_index + 1,
                    action=action,
                    workflow_status="running",
                    extra={"iteration": iteration, "tool_name": tool_name, "mcp_server_slug": slug, "arguments": compact_payload(arguments)},
                )
                tool_call = {
                    "id": f"workflow-action-{action_index + 1}-{iteration}",
                    "type": "function",
                    "function": {"name": tool_name, "arguments": compact_payload(arguments)},
                }
                call_record, tool_payload = invoke_tool_call(
                    tool_entity=tool_entity,
                    tool_call=tool_call,
                    platform_runtime=runtime_snapshot,
                    agent_id=context.agent_id,
                    agent_domain=agent_domain,
                    delegated_user_id=context.requested_by_user_id,
                    delegated_user_role=context.requested_by_role,
                )
                _complete_workflow_status(
                    progress=progress,
                    status_id=status_id,
                    kind="running_tool",
                    label=f"Completed workflow action {action_index + 1}",
                    summary=f"HTTP {int(call_record.get('status_code', 200) or 200)}",
                    state=state,
                    action_index=action_index + 1,
                    action=action,
                    workflow_status="running",
                    extra={"iteration": iteration, "tool_name": tool_name, "mcp_server_slug": slug, "result": compact_payload(tool_payload)},
                )
                tool_calls.append(call_record)
                state.setdefault("action_outputs", {})[str(action.get("id") or f"action_{action_index + 1}")] = tool_payload
                _store_output_variables(state, action, tool_payload)
                try:
                    evaluation, model_call, _ = _llm_json(
                        context=context,
                        runtime_snapshot=runtime_snapshot,
                        requested_model=requested_model,
                        system_prompt=action_prompt,
                        user_prompt=(
                            "Decide whether the workflow action is complete.\n"
                            "Return only JSON with complete:boolean, variables:object, follow_up_message:string.\n\n"
                            f"{_workflow_reference_guidance()}\n\n"
                            f"Workflow variable context:\n{dumps(_workflow_variable_context(variables=_workflow_available_variables(actions, before_index=action_index + 1), state=state))}\n\n"
                            f"Tool result:\n{compact_payload(tool_payload)}"
                        ),
                    )
                    if model_call:
                        model_calls.append(model_call)
                except LlmRuntimeClientError:
                    evaluation = {}
                for name, value in (evaluation.get("variables") if isinstance(evaluation.get("variables"), dict) else {}).items():
                    if str(name).strip() and str(value).strip():
                        state["variables"][str(name).strip()] = str(value).strip()
                if bool(evaluation.get("complete", True)):
                    action_completed = True
                    break
            if not action_completed:
                raise ExecutionBlockedError(
                    code="EXEC_WORKFLOW_ACTION_BLOCKED",
                    message=f"Workflow action '{str(action.get('name') or tool_name or slug)}' did not complete safely",
                    status_code=422,
                    details=_workflow_status_details(state=state, action_index=action_index + 1, action=action, workflow_status="blocked"),
                )
            action_index += 1
            state["action_index"] = action_index
            state["status"] = "running"
            continue

        if action_type == "send_output":
            available_variables = _workflow_available_variables(actions, before_index=action_index)
            selected_variable_names = {str(variable_name).strip() for variable_name in action.get("variable_refs", []) if str(variable_name).strip()}
            selected_variables = _workflow_variable_context(
                variables=[
                    variable
                    for variable in available_variables
                    if str(variable.get("name") or "").strip() in selected_variable_names
                ],
                state=state,
            )
            selected = {
                variable: state["variables"].get(str(variable))
                for variable in action.get("variable_refs", [])
                if str(variable) in state["variables"]
            }
            status_id = _start_workflow_status(
                progress=progress,
                kind="thinking",
                label=f"Composing workflow output {action_index + 1}",
                state=state,
                action_index=action_index + 1,
                action=action,
                workflow_status="running",
            )
            output, output_model_calls = _workflow_compose_output_with_repair(
                context=context,
                runtime_snapshot=runtime_snapshot,
                requested_model=requested_model,
                action_prompt=action_prompt,
                selected_variables=selected_variables,
                selected_values=selected,
            )
            model_calls.extend(output_model_calls)
            if not output:
                output = "\n".join(f"{key}: {compact_payload(value)}" for key, value in selected.items()) or "Workflow completed."
            state.update({"action_index": len(actions), "status": "completed"})
            _complete_workflow_status(
                progress=progress,
                status_id=status_id,
                kind="thinking",
                label=f"Completed workflow output {action_index + 1}",
                state=state,
                action_index=len(actions),
                action=action,
                workflow_status="completed",
            )
            return ExecutionResult(
                output_text=output,
                tool_calls=tool_calls,
                model_calls=model_calls,
                workflow_state=state,
                workflow_status="completed",
            ), requested_model

        raise ExecutionBlockedError(code="EXEC_INVALID_AGENT", message=f"Unknown workflow action '{action_type}'", status_code=422)
    state.update({"action_index": len(actions), "status": "completed"})
    return ExecutionResult(
        output_text="Workflow completed.",
        tool_calls=tool_calls,
        model_calls=model_calls,
        workflow_state=state,
        workflow_status="completed",
    ), requested_model


def _execute_model_call(
    *,
    context: ExecutionContext,
    agent_entity: dict[str, Any],
    model_ref: str | None,
    agent_tools: list[dict[str, Any]],
    progress: ProgressRecorder | None = None,
    delta_emit: DeltaEmitter | None = None,
) -> tuple[ExecutionResult, str | None]:
    progress = progress or ProgressRecorder()
    _raise_simulated_error_if_requested(context.execution_input)
    messages = list(context.conversation.messages)
    if not messages and context.conversation.retrieval_request is None:
        return _deterministic_execution_result(agent_id=context.agent_id, runtime_profile=context.runtime_profile), model_ref

    retrieval_request = context.conversation.retrieval_request
    retrieval_status_id: str | None = None
    if retrieval_request is not None:
        retrieval_status_id = progress.start(
            kind="retrieving",
            label=f"Retrieving information from: {retrieval_request.index}",
            summary=retrieval_request.query,
            details={
                "index": retrieval_request.index,
                "query": retrieval_request.query,
                "top_k": retrieval_request.top_k,
                "search_method": retrieval_request.search_method,
            },
        )
    try:
        embedding_call, retrieval_call, retrieval_results = execute_retrieval_call(
            retrieval_request=retrieval_request,
            platform_runtime=context.platform_runtime,
        )
    except Exception:
        if retrieval_status_id is not None:
            progress.fail(
                retrieval_status_id,
                kind="retrieving",
                label="Retrieval failed",
                details={
                    "index": retrieval_request.index if retrieval_request is not None else None,
                    "query": retrieval_request.query if retrieval_request is not None else None,
                },
            )
        raise
    if retrieval_status_id is not None and retrieval_call is not None:
        progress.complete(
            retrieval_status_id,
            kind="retrieving",
            label=f"Retrieved information from: {retrieval_call.get('index') or retrieval_request.index}",
            summary=f"{int(retrieval_call.get('result_count', 0) or 0)} results",
            details={
                "index": retrieval_call.get("index"),
                "query": retrieval_call.get("query"),
                "top_k": retrieval_call.get("top_k"),
                "search_method": retrieval_call.get("search_method"),
                "result_count": retrieval_call.get("result_count"),
                "results": summarize_results(retrieval_call.get("results")),
            },
        )
    agent_spec = _agent_current_spec(agent_entity)
    agent_domain = str(agent_spec.get("agent_domain") or "default").strip() or "default"
    effective_messages = _prepend_agent_instructions(messages, agent_spec=agent_spec)
    effective_messages = prepend_retrieval_context(
        effective_messages,
        retrieval_results=retrieval_results,
        retrieval_instructions=_agent_retrieval_instructions(agent_spec),
        after_leading_system_messages=True,
    )

    runtime_snapshot = context.platform_runtime if isinstance(context.platform_runtime, dict) else {}
    requested_model_override = str(context.execution_input.get("model", "")).strip() or None
    effective_requested_model = requested_model_override or model_ref
    tool_lookup: dict[str, dict[str, Any]] = {}
    tool_definitions: list[dict[str, Any]] = []
    for tool_entity in agent_tools:
        tool_spec = effective_tool_spec(tool_entity)
        tool_name = str(tool_spec.get("exposed_tool_name") or tool_spec.get("tool_name") or "").strip()
        if not tool_name:
            continue
        runtime_capability = runtime_capability_for_tool_spec(tool_spec)
        resolve_tool_runtime_binding(platform_runtime=runtime_snapshot, capability_key=runtime_capability)
        tool_lookup[tool_name] = tool_entity
        tool_definitions.append(build_tool_definition(tool_entity))

    model_calls: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    connect_status_id = progress.start(
        kind="connecting",
        label="Connecting to model runtime",
        details=model_status_details(runtime_snapshot, effective_requested_model),
    )
    try:
        client = build_llm_runtime_client(runtime_snapshot)
    except LlmRuntimeClientError as exc:
        progress.fail(
            connect_status_id,
            kind="connecting",
            label="Model runtime connection failed",
            details={**model_status_details(runtime_snapshot, effective_requested_model), "error": compact_payload(exc.details)},
        )
        if exc.code == "runtime_timeout":
            raise ExecutionBlockedError(code="EXEC_TIMEOUT", message="Execution timed out", status_code=504, details=exc.details) from exc
        if exc.code in {"runtime_unreachable", "runtime_upstream_unavailable"}:
            raise ExecutionBlockedError(code="EXEC_UPSTREAM_UNAVAILABLE", message="Upstream LLM/tool dependency unavailable", status_code=503, details=exc.details) from exc
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500, details=exc.details) from exc
    progress.complete(
        connect_status_id,
        kind="connecting",
        label="Connected to model runtime",
        details=model_status_details(runtime_snapshot, effective_requested_model),
    )

    llm_binding = runtime_snapshot.get("capabilities", {}).get("llm_inference", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    effective_model = effective_requested_model
    completion: dict[str, Any] | None = None
    generation_status_id = progress.start(
        kind="generating",
        label="Generating response",
        details=model_status_details(runtime_snapshot, effective_requested_model),
    )
    for _round_index in range(_MAX_TOOL_CALL_ROUNDS):
        try:
            if delta_emit is not None and not tool_definitions:
                completion = stream_model_completion(
                    client=client,
                    runtime_snapshot=runtime_snapshot,
                    requested_model=effective_requested_model,
                    messages=effective_messages,
                    progress=progress,
                    delta_emit=delta_emit,
                )
            else:
                completion = client.chat_completion(
                    requested_model=effective_requested_model,
                    messages=effective_messages,
                    tools=tool_definitions or None,
                )
        except LlmRuntimeClientError as exc:
            progress.fail(
                generation_status_id,
                kind="generating",
                label="Response generation failed",
                details={**model_status_details(runtime_snapshot, effective_requested_model), "error": compact_payload(exc.details)},
            )
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
                progress.fail(
                    generation_status_id,
                    kind="generating",
                    label="Response generation failed",
                    details={"reason": "tool_not_allowed", "tool_name": tool_name},
                )
                raise ExecutionBlockedError(
                    code="EXEC_TOOL_NOT_ALLOWED",
                    message=f"Tool '{tool_name}' referenced by the model is not allowed",
                    status_code=403,
                )
            arguments = _tool_arguments(tool_call)
            tool_status_id = progress.start(
                kind="searching_web" if tool_name == "web_search" else "running_tool",
                label=_tool_status_label(tool_name, arguments),
                details={"tool_name": tool_name, "arguments": compact_payload(arguments)},
            )
            try:
                call_record, tool_payload = invoke_tool_call(
                    tool_entity=tool_entity,
                    tool_call=tool_call,
                    platform_runtime=runtime_snapshot,
                    agent_id=context.agent_id,
                    agent_domain=agent_domain,
                    delegated_user_id=context.requested_by_user_id,
                    delegated_user_role=context.requested_by_role,
                )
            except Exception:
                progress.fail(
                    tool_status_id,
                    kind="searching_web" if tool_name == "web_search" else "running_tool",
                    label=f"{_tool_status_label(tool_name, arguments)} failed",
                    details={"tool_name": tool_name, "arguments": compact_payload(arguments)},
                )
                raise
            progress.complete(
                tool_status_id,
                kind="searching_web" if tool_name == "web_search" else "running_tool",
                label=_tool_status_label(tool_name, arguments),
                summary=f"HTTP {int(call_record.get('status_code', 200) or 200)}",
                details={
                    "tool_name": tool_name,
                    "arguments": compact_payload(arguments),
                    "result": compact_payload(call_record.get("result") or call_record.get("error") or tool_payload),
                },
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
        progress.fail(
            generation_status_id,
            kind="generating",
            label="Response generation failed",
            details={"reason": "tool_round_limit_exceeded"},
        )
        raise ExecutionBlockedError(
            code="EXEC_INTERNAL_ERROR",
            message="Execution failed internally",
            status_code=500,
            details={"reason": "tool_round_limit_exceeded"},
        )

    if completion is None:
        progress.fail(generation_status_id, kind="generating", label="Response generation failed")
        raise ExecutionBlockedError(code="EXEC_INTERNAL_ERROR", message="Execution failed internally", status_code=500)

    progress.complete(
        generation_status_id,
        kind="generating",
        label="Generated response",
        summary=f"{len(str(completion.get('output_text', '')))} characters",
        details=model_status_details(runtime_snapshot, effective_model),
    )

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


def create_execution(payload: dict[str, Any], progress_emit=None, delta_emit: DeltaEmitter | None = None) -> tuple[dict[str, Any], int]:
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

    progress = ProgressRecorder(progress_emit)
    thinking_status_id = progress.start(
        kind="thinking",
        label="Thinking",
        details={"agent_id": agent_id, "runtime_profile": runtime_profile},
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
        progress.complete(
            thinking_status_id,
            kind="thinking",
            label="Planned execution",
            details={
                "agent_id": agent_id,
                "agent_version": agent_version,
                "tool_count": len(agent_tools),
            },
        )
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
            agent_entity=agent_entity,
            model_ref=model_ref,
            agent_tools=agent_tools,
            progress=progress,
            delta_emit=delta_emit,
        ) if _agent_type(_agent_current_spec(agent_entity)) != "workflow" else _execute_workflow_agent(
            context=context,
            agent_entity=agent_entity,
            agent_tools=agent_tools,
            progress=progress,
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
        progress.fail(
            thinking_status_id,
            kind="thinking",
            label="Execution blocked",
            details={"error": exc.code, "message": exc.message},
        )
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
        progress.fail(
            thinking_status_id,
            kind="thinking",
            label="Execution failed",
            details={"error": "EXEC_INTERNAL_ERROR", "message": str(exc)},
        )
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


def create_execution_stream(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    events: Queue[dict[str, Any] | None] = Queue()

    def _emit_status(status: dict[str, Any]) -> None:
        events.put({"event": "status", "data": status})

    def _emit_delta(delta: dict[str, Any]) -> None:
        events.put({"event": "delta", "data": delta})

    def _run() -> None:
        try:
            response_payload, status_code = create_execution(payload, progress_emit=_emit_status, delta_emit=_emit_delta)
            events.put({"event": "complete", "data": {**response_payload, "status_code": status_code}})
        except ExecutionBlockedError as exc:
            events.put(
                {
                    "event": "error",
                    "data": {
                        "error": exc.code,
                        "message": exc.message,
                        "status_code": exc.status_code,
                        "details": exc.details,
                    },
                }
            )
        except ValueError as exc:
            events.put(
                {
                    "event": "error",
                    "data": {
                        "error": str(exc) or "invalid_payload",
                        "message": "Expected valid payload",
                        "status_code": 400,
                    },
                }
            )
        finally:
            events.put(None)

    Thread(target=_run, daemon=True).start()
    while True:
        event = events.get()
        if event is None:
            return
        yield event


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
