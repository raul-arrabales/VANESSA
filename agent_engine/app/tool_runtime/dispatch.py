from __future__ import annotations

from json import dumps, loads
from typing import Any

from ..services.policy_runtime_gate import ExecutionBlockedError
from ..services.runtime_client import (
    ToolRuntimeClientError,
    build_mcp_tool_runtime_client,
    build_sandbox_tool_runtime_client,
)


def runtime_capability_for_transport(transport: str) -> str:
    normalized = transport.strip().lower()
    if normalized == "mcp":
        return "mcp_runtime"
    if normalized == "sandbox_http":
        return "sandbox_execution"
    raise ExecutionBlockedError(
        code="EXEC_TOOL_NOT_ALLOWED",
        message=f"Unsupported tool transport '{transport}'",
        status_code=403,
    )


def build_tool_definition(tool_entity: dict[str, Any]) -> dict[str, Any]:
    tool_spec = tool_entity.get("current_spec") if isinstance(tool_entity.get("current_spec"), dict) else {}
    return {
        "type": "function",
        "function": {
            "name": str(tool_spec.get("tool_name", "")).strip(),
            "description": str(tool_spec.get("description", "")).strip(),
            "parameters": dict(tool_spec.get("input_schema") or {}),
        },
    }


def tool_message_content(payload: Any) -> list[dict[str, str]]:
    return [{"type": "text", "text": dumps(payload, sort_keys=True, separators=(",", ":"))}]


def resolve_tool_runtime_binding(*, platform_runtime: dict[str, Any], capability_key: str) -> dict[str, Any]:
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    binding = capabilities.get(capability_key)
    if not isinstance(binding, dict):
        raise ExecutionBlockedError(
            code="EXEC_TOOL_NOT_ALLOWED",
            message=f"Active platform runtime is missing capability '{capability_key}'",
            status_code=403,
        )
    return binding


def _map_tool_runtime_error(exc: ToolRuntimeClientError) -> ExecutionBlockedError:
    if exc.code == "tool_runtime_timeout":
        return ExecutionBlockedError(
            code="EXEC_TIMEOUT",
            message="Execution timed out",
            status_code=504,
            details=exc.details,
        )
    if exc.code in {"tool_runtime_unreachable", "tool_runtime_upstream_unavailable"}:
        return ExecutionBlockedError(
            code="EXEC_UPSTREAM_UNAVAILABLE",
            message="Upstream LLM/tool dependency unavailable",
            status_code=503,
            details=exc.details,
        )
    return ExecutionBlockedError(
        code="EXEC_INTERNAL_ERROR",
        message="Execution failed internally",
        status_code=500,
        details=exc.details,
    )


def invoke_tool_call(
    *,
    tool_entity: dict[str, Any],
    tool_call: dict[str, Any],
    platform_runtime: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    tool_spec = tool_entity.get("current_spec") if isinstance(tool_entity.get("current_spec"), dict) else {}
    transport = str(tool_spec.get("transport", "")).strip().lower()
    runtime_capability = runtime_capability_for_transport(transport)
    binding = resolve_tool_runtime_binding(platform_runtime=platform_runtime, capability_key=runtime_capability)
    deployment_profile = platform_runtime.get("deployment_profile") if isinstance(platform_runtime.get("deployment_profile"), dict) else {}
    arguments_text = str(((tool_call.get("function") or {}).get("arguments", "")))
    try:
        arguments = loads(arguments_text) if arguments_text.strip() else {}
    except ValueError:
        error_payload = {
            "code": "invalid_arguments",
            "message": "Model returned invalid tool arguments",
            "raw_arguments": arguments_text,
        }
        return (
            {
                "tool_ref": tool_entity.get("entity_id"),
                "tool_name": tool_spec.get("tool_name"),
                "transport": transport,
                "runtime_capability": runtime_capability,
                "provider_slug": binding.get("slug"),
                "provider_key": binding.get("provider_key"),
                "deployment_profile_slug": deployment_profile.get("slug"),
                "status_code": 400,
                "arguments": {},
                "error": error_payload,
            },
            error_payload,
        )
    if not isinstance(arguments, dict):
        error_payload = {
            "code": "invalid_arguments",
            "message": "Model returned non-object tool arguments",
        }
        return (
            {
                "tool_ref": tool_entity.get("entity_id"),
                "tool_name": tool_spec.get("tool_name"),
                "transport": transport,
                "runtime_capability": runtime_capability,
                "provider_slug": binding.get("slug"),
                "provider_key": binding.get("provider_key"),
                "deployment_profile_slug": deployment_profile.get("slug"),
                "status_code": 400,
                "arguments": arguments,
                "error": error_payload,
            },
            error_payload,
        )

    try:
        if transport == "mcp":
            runtime_client = build_mcp_tool_runtime_client(platform_runtime)
            runtime_payload = runtime_client.invoke(
                tool_name=str(tool_spec.get("tool_name", "")).strip(),
                arguments=arguments,
                request_metadata={"tool_ref": tool_entity.get("entity_id")},
            )
        elif transport == "sandbox_http":
            runtime_client = build_sandbox_tool_runtime_client(platform_runtime)
            safety_policy = dict(tool_spec.get("safety_policy") or {})
            timeout_seconds = int(arguments.get("timeout_seconds") or safety_policy.get("timeout_seconds") or 5)
            runtime_payload = runtime_client.execute_python(
                code=str(arguments.get("code", "")),
                input_payload=arguments.get("input"),
                timeout_seconds=timeout_seconds,
                policy=safety_policy,
            )
        else:
            raise ToolRuntimeClientError(
                code="unsupported_adapter_kind",
                message="Unsupported tool runtime adapter",
                status_code=500,
            )
    except ToolRuntimeClientError as exc:
        raise _map_tool_runtime_error(exc) from exc

    status_code = int(runtime_payload.get("status_code", 200) or 200)
    result_payload = runtime_payload.get("result")
    error_payload = runtime_payload.get("error")
    call_record = {
        "tool_ref": tool_entity.get("entity_id"),
        "tool_name": tool_spec.get("tool_name"),
        "transport": transport,
        "runtime_capability": runtime_capability,
        "provider_slug": binding.get("slug"),
        "provider_key": binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
        "status_code": status_code,
        "arguments": arguments,
    }
    if error_payload is not None:
        call_record["error"] = error_payload
        return call_record, error_payload
    call_record["result"] = result_payload
    return call_record, result_payload
