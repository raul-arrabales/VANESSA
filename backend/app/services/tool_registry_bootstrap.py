from __future__ import annotations

from ..repositories.registry import create_registry_entity, create_registry_version, find_registry_entity, list_registry_versions
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
                "language": {"type": "string"},
                "time_range": {"type": "string", "enum": ["day", "month", "year"]},
                "safesearch": {"type": "integer", "enum": [0, 1, 2]},
                "categories": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"},
                            "engine": {"type": "string"},
                            "rank": {"type": "integer"},
                        },
                        "required": ["title", "url", "snippet", "engine", "rank"],
                        "additionalProperties": True,
                    },
                },
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


def _next_builtin_version(database_url: str, *, entity_id: str, current_version: object) -> str:
    version_numbers: list[int] = []
    for row in list_registry_versions(database_url, entity_id=entity_id):
        raw = str(row.get("version") or "").strip().lower()
        if raw.startswith("v") and raw[1:].isdigit():
            version_numbers.append(int(raw[1:]))
    raw_current = str(current_version or "").strip().lower()
    if raw_current.startswith("v") and raw_current[1:].isdigit():
        version_numbers.append(int(raw_current[1:]))
    return f"v{(max(version_numbers) if version_numbers else 1) + 1}"


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
            continue
        current_spec = existing.get("current_spec") if isinstance(existing.get("current_spec"), dict) else {}
        if entity_id == "tool.web_search" and current_spec != spec:
            create_registry_version(
                database_url,
                entity_id=entity_id,
                version=_next_builtin_version(
                    database_url,
                    entity_id=entity_id,
                    current_version=existing.get("current_version"),
                ),
                spec_json=dict(spec),
                set_current=True,
                published=True,
            )
    return True
