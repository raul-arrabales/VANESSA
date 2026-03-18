from __future__ import annotations

from ..repositories.registry import create_registry_entity, create_registry_version, find_registry_entity
from ..repositories.users import list_users

_BUILTIN_TOOLS: dict[str, dict[str, object]] = {
    "tool.web_search": {
        "name": "Web Search",
        "description": "Searches the web through the MCP runtime gateway.",
        "transport": "mcp",
        "connection_profile_ref": "default",
        "tool_name": "web_search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {"type": "array"},
            },
            "required": ["query", "results"],
            "additionalProperties": True,
        },
        "safety_policy": {
            "timeout_seconds": 8,
            "network_access": True,
        },
        "offline_compatible": False,
    },
    "tool.python_exec": {
        "name": "Python Execution",
        "description": "Runs constrained Python code in the sandbox runtime.",
        "transport": "sandbox_http",
        "connection_profile_ref": "default",
        "tool_name": "python_exec",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "input": {},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["code"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "result": {},
                "error": {},
            },
            "required": ["stdout", "stderr"],
            "additionalProperties": True,
        },
        "safety_policy": {
            "timeout_seconds": 5,
            "network_access": False,
            "allow_imports": False,
        },
        "offline_compatible": True,
    },
}


def _select_owner_user_id(database_url: str) -> int | None:
    users = list_users(database_url, is_active=True)
    if not users:
        users = list_users(database_url, is_active=None)
    if not users:
        return None
    for user in users:
        if str(user.get("role", "")).strip().lower() == "superadmin":
            return int(user["id"])
    return int(users[0]["id"])


def ensure_builtin_tools(database_url: str) -> bool:
    owner_user_id = _select_owner_user_id(database_url)
    if owner_user_id is None:
        return False

    for entity_id, spec in _BUILTIN_TOOLS.items():
        existing = find_registry_entity(database_url, entity_type="tool", entity_id=entity_id)
        if existing is None:
            create_registry_entity(
                database_url,
                entity_id=entity_id,
                entity_type="tool",
                owner_user_id=owner_user_id,
                visibility="private",
                status="draft",
            )
            create_registry_version(
                database_url,
                entity_id=entity_id,
                version="v1",
                spec_json=dict(spec),
                set_current=True,
                published=True,
            )
            continue
        if existing.get("current_version") is None:
            create_registry_version(
                database_url,
                entity_id=entity_id,
                version="v1",
                spec_json=dict(spec),
                set_current=True,
                published=True,
            )
    return True
