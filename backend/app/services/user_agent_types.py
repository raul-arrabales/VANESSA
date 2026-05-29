from __future__ import annotations

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


def default_workflow_definition() -> dict[str, Any]:
    return {"steps": []}


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
    steps_raw = value.get("steps", [])
    if not isinstance(steps_raw, list):
        raise ValueError("workflow_definition.steps must be an array")
    steps: list[dict[str, Any]] = []
    for index, item in enumerate(steps_raw):
        if not isinstance(item, dict):
            raise ValueError(f"workflow_definition.steps[{index}] must be an object")
        step_id = str(item.get("id") or f"step_{index + 1}").strip() or f"step_{index + 1}"
        name = str(item.get("name") or step_id.replace("_", " ").replace("-", " ")).strip() or step_id
        mcp_server_slug = str(item.get("mcp_server_slug") or "").strip()
        exposed_tool_name = str(item.get("exposed_tool_name") or "").strip()
        if not mcp_server_slug:
            raise ValueError(f"workflow_definition.steps[{index}].mcp_server_slug is required")
        if not exposed_tool_name:
            raise ValueError(f"workflow_definition.steps[{index}].exposed_tool_name is required")
        raw_arguments = item.get("arguments")
        if raw_arguments is None:
            arguments: dict[str, Any] = {}
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            raise ValueError(f"workflow_definition.steps[{index}].arguments must be an object")
        steps.append(
            {
                "id": step_id,
                "name": name,
                "mcp_server_slug": mcp_server_slug,
                "exposed_tool_name": exposed_tool_name,
                "arguments": arguments,
            }
        )
    return {"steps": steps}


def workflow_step_server_slugs(workflow_definition: dict[str, Any]) -> list[str]:
    steps = workflow_definition.get("steps") if isinstance(workflow_definition.get("steps"), list) else []
    slugs: list[str] = []
    for item in steps:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("mcp_server_slug") or "").strip()
        if slug:
            slugs.append(slug)
    return slugs
