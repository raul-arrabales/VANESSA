from __future__ import annotations

from typing import Any, Literal

from .agent_prompt_defaults import coerce_agent_runtime_prompts, normalize_agent_runtime_prompts
from .user_agent_types import (
    CHANNEL_TYPE_VANESSA_WEBAPP,
    INTERFACE_TYPE_CHAT,
    coerce_channel_type,
    coerce_interface_type,
    coerce_user_agent_type,
    coerce_workflow_execution_mode,
    normalize_workflow_definition,
    normalize_workflow_definition_for_response,
)

WorkflowDefinitionMode = Literal["stored", "response"]


class UserAgentSpecValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def coerce_runtime_constraints(value: Any) -> dict[str, bool]:
    runtime_constraints = value
    if not isinstance(runtime_constraints, dict):
        raise UserAgentSpecValidationError("invalid_runtime_constraints", "runtime_constraints must be an object")
    if not isinstance(runtime_constraints.get("internet_required"), bool):
        raise UserAgentSpecValidationError(
            "invalid_runtime_constraints",
            "runtime_constraints.internet_required must be a boolean",
        )
    if not isinstance(runtime_constraints.get("sandbox_required"), bool):
        raise UserAgentSpecValidationError(
            "invalid_runtime_constraints",
            "runtime_constraints.sandbox_required must be a boolean",
        )
    return {
        "internet_required": bool(runtime_constraints["internet_required"]),
        "sandbox_required": bool(runtime_constraints["sandbox_required"]),
    }


def coerce_user_agent_common_spec(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    instructions = str(payload.get("instructions", "")).strip()
    if not name:
        raise UserAgentSpecValidationError("invalid_name", "name is required")
    if not description:
        raise UserAgentSpecValidationError("invalid_description", "description is required")
    try:
        agent_type = coerce_user_agent_type(payload.get("agent_type"))
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_agent_type", str(exc)) from exc
    if agent_type != "workflow" and not instructions:
        raise UserAgentSpecValidationError("invalid_instructions", "instructions is required")
    try:
        channel_type = coerce_channel_type(payload.get("channel_type"))
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_channel_type", str(exc)) from exc
    try:
        interface_type = coerce_interface_type(payload.get("interface_type"))
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_interface_type", str(exc)) from exc
    try:
        coerced_runtime_prompts = coerce_agent_runtime_prompts(
            payload.get("runtime_prompts"),
            default_when_missing=True,
            agent_type=agent_type,
        )
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_runtime_prompts", str(exc)) from exc
    tool_refs_raw = payload.get("tool_refs", [])
    if not isinstance(tool_refs_raw, list):
        raise UserAgentSpecValidationError("invalid_tool_refs", "tool_refs must be an array")
    mcp_server_refs_raw = payload.get("mcp_server_refs", [])
    if not isinstance(mcp_server_refs_raw, list):
        raise UserAgentSpecValidationError("invalid_mcp_server_refs", "mcp_server_refs must be an array")
    try:
        workflow_definition = normalize_workflow_definition(payload.get("workflow_definition"))
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_workflow_definition", str(exc)) from exc
    try:
        workflow_execution_mode = coerce_workflow_execution_mode(payload.get("workflow_execution_mode"))
    except ValueError as exc:
        raise UserAgentSpecValidationError("invalid_workflow_execution_mode", str(exc)) from exc
    runtime_constraints = coerce_runtime_constraints(payload.get("runtime_constraints"))
    if channel_type == CHANNEL_TYPE_VANESSA_WEBAPP and interface_type != INTERFACE_TYPE_CHAT:
        raise UserAgentSpecValidationError(
            "invalid_interface_type",
            "channel_type vanessa_webapp currently requires interface_type chat",
        )
    default_model_ref_raw = payload.get("default_model_ref")
    default_model_ref = str(default_model_ref_raw).strip() if default_model_ref_raw is not None else None
    return {
        "name": name,
        "description": description,
        "instructions": instructions,
        "runtime_prompts": coerced_runtime_prompts,
        "default_model_ref": default_model_ref or None,
        "tool_refs": [str(item).strip() for item in tool_refs_raw if str(item).strip()],
        "mcp_server_refs": [str(item).strip() for item in mcp_server_refs_raw if str(item).strip()],
        "agent_domain": str(payload.get("agent_domain") or "default").strip() or "default",
        "agent_type": agent_type,
        "channel_type": channel_type,
        "interface_type": interface_type,
        "workflow_definition": workflow_definition,
        "workflow_execution_mode": workflow_execution_mode,
        "runtime_constraints": runtime_constraints,
    }


def serialize_user_agent_spec(
    spec: dict[str, Any],
    *,
    include_tool_policy: bool = False,
    workflow_definition_mode: WorkflowDefinitionMode = "stored",
) -> dict[str, Any]:
    normalized = dict(spec)
    raw_runtime_prompts = normalized.get("runtime_prompts")
    agent_type = str(normalized.get("agent_type") or "workflow").strip() or "workflow"
    workflow_definition = (
        normalize_workflow_definition_for_response(
            normalized.get("workflow_definition"),
            runtime_prompts=raw_runtime_prompts,
        )
        if workflow_definition_mode == "response"
        else normalize_workflow_definition(normalized.get("workflow_definition"))
    )
    serialized = {
        "name": str(normalized.get("name", "")),
        "description": str(normalized.get("description", "")),
        "instructions": str(normalized.get("instructions", "")),
        "runtime_prompts": normalize_agent_runtime_prompts(
            raw_runtime_prompts,
            agent_type=agent_type,
        ),
        "default_model_ref": _string_or_none(normalized.get("default_model_ref")),
        "tool_refs": list(normalized.get("tool_refs") or []),
        "mcp_server_refs": list(normalized.get("mcp_server_refs") or []),
        "agent_domain": str(normalized.get("agent_domain") or "default").strip() or "default",
        "agent_type": agent_type,
        "channel_type": str(normalized.get("channel_type") or CHANNEL_TYPE_VANESSA_WEBAPP).strip() or CHANNEL_TYPE_VANESSA_WEBAPP,
        "interface_type": str(normalized.get("interface_type") or INTERFACE_TYPE_CHAT).strip() or INTERFACE_TYPE_CHAT,
        "workflow_definition": workflow_definition,
        "workflow_execution_mode": str(normalized.get("workflow_execution_mode") or "one_time").strip() or "one_time",
        "runtime_constraints": dict(normalized.get("runtime_constraints") or {}),
    }
    if include_tool_policy:
        serialized["tool_policy"] = dict(normalized.get("tool_policy") or {})
    return serialized


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
