from __future__ import annotations

import re
from typing import Any

USER_AGENT_TYPE_WORKFLOW = "workflow"
USER_AGENT_TYPE_PLANNER = "planner"
USER_AGENT_TYPE_REACT = "react"
SUPPORTED_USER_AGENT_TYPES = {
    USER_AGENT_TYPE_WORKFLOW,
    USER_AGENT_TYPE_PLANNER,
    USER_AGENT_TYPE_REACT,
}
CREATABLE_USER_AGENT_TYPES = {USER_AGENT_TYPE_WORKFLOW}

CHANNEL_TYPE_VANESSA_WEBAPP = "vanessa_webapp"
SUPPORTED_CHANNEL_TYPES = {CHANNEL_TYPE_VANESSA_WEBAPP}

INTERFACE_TYPE_CHAT = "chat"
SUPPORTED_INTERFACE_TYPES = {INTERFACE_TYPE_CHAT}
WORKFLOW_VARIABLE_TYPE_TEXT = "text"
SUPPORTED_WORKFLOW_VARIABLE_TYPES = {WORKFLOW_VARIABLE_TYPE_TEXT}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def default_workflow_definition() -> dict[str, Any]:
    return {"version": 2, "actions": []}


def coerce_user_agent_type(value: Any) -> str:
    normalized = str(value or USER_AGENT_TYPE_WORKFLOW).strip().lower() or USER_AGENT_TYPE_WORKFLOW
    if normalized not in SUPPORTED_USER_AGENT_TYPES:
        raise ValueError("agent_type must be workflow, planner, or react")
    return normalized


def coerce_channel_type(value: Any) -> str:
    normalized = str(value or CHANNEL_TYPE_VANESSA_WEBAPP).strip().lower() or CHANNEL_TYPE_VANESSA_WEBAPP
    if normalized not in SUPPORTED_CHANNEL_TYPES:
        raise ValueError("channel_type must be vanessa_webapp")
    return normalized


def coerce_interface_type(value: Any) -> str:
    normalized = str(value or INTERFACE_TYPE_CHAT).strip().lower() or INTERFACE_TYPE_CHAT
    if normalized not in SUPPORTED_INTERFACE_TYPES:
        raise ValueError("interface_type must be chat")
    return normalized


def normalize_workflow_definition(value: Any) -> dict[str, Any]:
    if value is None:
        return default_workflow_definition()
    if not isinstance(value, dict):
        raise ValueError("workflow_definition must be an object")
    if "steps" in value:
        raise ValueError("workflow_definition.steps is retired; use workflow_definition.actions")
    if int(value.get("version", 2) or 2) != 2:
        raise ValueError("workflow_definition.version must be 2")
    actions_raw = value.get("actions", [])
    if not isinstance(actions_raw, list):
        raise ValueError("workflow_definition.actions must be an array")
    actions: list[dict[str, Any]] = []
    produced_variables: set[str] = set()
    for index, item in enumerate(actions_raw):
        if not isinstance(item, dict):
            raise ValueError(f"workflow_definition.actions[{index}] must be an object")
        action_type = str(item.get("type") or "").strip()
        if action_type not in {"get_user_input", "mcp_tool", "send_output"}:
            raise ValueError(f"workflow_definition.actions[{index}].type is invalid")
        action_id = str(item.get("id") or f"{action_type}_{index + 1}").strip() or f"{action_type}_{index + 1}"
        name = str(item.get("name") or action_type.replace("_", " ")).strip() or action_type
        if action_type == "get_user_input":
            variables = _normalize_workflow_variables(item.get("variables"), f"workflow_definition.actions[{index}].variables", produced_variables)
            prompt = str(item.get("prompt") or "").strip()
            if not prompt:
                raise ValueError(f"workflow_definition.actions[{index}].prompt is required")
            actions.append({
                "id": action_id,
                "type": action_type,
                "name": name,
                "prompt": prompt,
                "variables": variables,
            })
            continue
        if action_type == "mcp_tool":
            mcp_server_slug = str(item.get("mcp_server_slug") or "").strip()
            exposed_tool_name = str(item.get("exposed_tool_name") or "").strip()
            prompt = str(item.get("prompt") or "").strip()
            if not mcp_server_slug:
                raise ValueError(f"workflow_definition.actions[{index}].mcp_server_slug is required")
            if not exposed_tool_name:
                raise ValueError(f"workflow_definition.actions[{index}].exposed_tool_name is required")
            if not prompt:
                raise ValueError(f"workflow_definition.actions[{index}].prompt is required")
            input_bindings = item.get("input_bindings")
            if not isinstance(input_bindings, dict):
                raise ValueError(f"workflow_definition.actions[{index}].input_bindings must be an object")
            normalized_bindings: dict[str, dict[str, str]] = {}
            for field_name, binding in input_bindings.items():
                if not isinstance(binding, dict):
                    raise ValueError(f"workflow_definition.actions[{index}].input_bindings.{field_name} must be an object")
                variable = str(binding.get("variable") or "").strip()
                if variable:
                    normalized_bindings[str(field_name)] = {"variable": variable}
            output_variables = _normalize_workflow_variables(
                item.get("output_variables"),
                f"workflow_definition.actions[{index}].output_variables",
                produced_variables,
                allow_path=True,
            )
            actions.append({
                "id": action_id,
                "type": action_type,
                "name": name,
                "mcp_server_slug": mcp_server_slug,
                "exposed_tool_name": exposed_tool_name,
                "prompt": prompt,
                "input_bindings": normalized_bindings,
                "output_variables": output_variables,
            })
            continue
        variable_refs_raw = item.get("variable_refs", [])
        prompt = str(item.get("prompt") or "").strip()
        if not isinstance(variable_refs_raw, list):
            raise ValueError(f"workflow_definition.actions[{index}].variable_refs must be an array")
        if not prompt:
            raise ValueError(f"workflow_definition.actions[{index}].prompt is required")
        actions.append({
            "id": action_id,
            "type": action_type,
            "name": name,
            "prompt": prompt,
            "variable_refs": [str(variable).strip() for variable in variable_refs_raw if str(variable).strip()],
        })
    return {"version": 2, "actions": actions}


def _normalize_workflow_variables(value: Any, path: str, produced_variables: set[str], *, allow_path: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} must be a non-empty array")
    variables: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}[{index}] must be an object")
        name = str(item.get("name") or "").strip()
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"{path}[{index}].name must be a valid identifier")
        if name in produced_variables:
            raise ValueError(f"workflow variable '{name}' is defined more than once")
        label = str(item.get("label") or "").strip()
        if not label:
            raise ValueError(f"{path}[{index}].label is required")
        variable_type = coerce_workflow_variable_type(item.get("type"))
        produced_variables.add(name)
        normalized = {
            "name": name,
            "label": label,
            "type": variable_type,
            "required": bool(item.get("required", True)),
        }
        guidance = str(item.get("guidance") or "").strip()
        if guidance:
            normalized["guidance"] = guidance
        if allow_path:
            output_path = str(item.get("path") or "").strip()
            if output_path:
                normalized["path"] = output_path
        variables.append(normalized)
    return variables


def workflow_actions(workflow_definition: dict[str, Any]) -> list[dict[str, Any]]:
    actions = workflow_definition.get("actions") if isinstance(workflow_definition.get("actions"), list) else []
    return [action for action in actions if isinstance(action, dict)]


def workflow_mcp_server_slugs(workflow_definition: dict[str, Any]) -> list[str]:
    actions = workflow_actions(workflow_definition)
    slugs: list[str] = []
    for item in actions:
        if str(item.get("type") or "") != "mcp_tool":
            continue
        slug = str(item.get("mcp_server_slug") or "").strip()
        if slug:
            slugs.append(slug)
    return slugs

def coerce_workflow_variable_type(value: Any) -> str:
    normalized = str(value or WORKFLOW_VARIABLE_TYPE_TEXT).strip().lower() or WORKFLOW_VARIABLE_TYPE_TEXT
    if normalized not in SUPPORTED_WORKFLOW_VARIABLE_TYPES:
        raise ValueError("workflow variable type must be text")
    return normalized
