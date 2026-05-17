from __future__ import annotations

from ..repositories.catalog_runtime import upsert_mcp_server_status, upsert_tool_runtime_status
from ..repositories.registry import create_registry_entity, create_registry_version, find_registry_entity, list_registry_versions
from ..repositories.users import list_users

_BUILTIN_TOOLS: dict[str, dict[str, object]] = {
    "tool.web_search": {
        "name": "Web Search",
        "description": "Searches the web through the MCP gateway's SearXNG-backed runner.",
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
        "execution_backend": "mcp_gateway_web_search",
        "execution_config": {
            "internal_tool_name": "web_search",
            "gateway_internal_path": "/v1/internal/tools/web-search",
        },
        "permissions": {},
    },
    "tool.python_exec": {
        "name": "Python Execution",
        "description": "Runs constrained Python code in the sandbox runtime.",
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
        "execution_backend": "sandbox_python",
        "execution_config": {},
        "permissions": {},
    },
}

_DEFAULT_MCP_AUTHORIZATION_POLICY: dict[str, list[str]] = {
    "agent_ids": ["*"],
    "agent_domains": ["*"],
    "agent_roles": ["*"],
    "user_roles": ["*"],
    "user_ids": ["*"],
    "user_group_ids": ["*"],
}

_BUILTIN_MCP_SERVERS: dict[str, dict[str, object]] = {
    "mcp.web_search": {
        "name": "Web Search MCP",
        "slug": "web_search",
        "description": "Expose the internal web search tool through the MCP gateway.",
        "backing_tool_id": "tool.web_search",
        "exposed_tool_name": "web_search",
        "input_schema": _BUILTIN_TOOLS["tool.web_search"]["input_schema"],
        "output_schema": _BUILTIN_TOOLS["tool.web_search"]["output_schema"],
        "metadata": {
            "category": "web_search",
            "capabilities": ["web-search", "fresh-information", "source-discovery", "fact-checking", "public-research"],
            "local": False,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "public_web",
            "output_freshness": "fresh",
            "audit_level": "standard",
        },
        "authorization_policy": _DEFAULT_MCP_AUTHORIZATION_POLICY,
        "enabled": True,
    },
    "mcp.python_exec": {
        "name": "Python Execution MCP",
        "slug": "python_exec",
        "description": "Expose the internal Python execution tool through the MCP gateway.",
        "backing_tool_id": "tool.python_exec",
        "exposed_tool_name": "python_exec",
        "input_schema": _BUILTIN_TOOLS["tool.python_exec"]["input_schema"],
        "output_schema": _BUILTIN_TOOLS["tool.python_exec"]["output_schema"],
        "metadata": {
            "category": "code_execution",
            "capabilities": ["python", "code-execution", "calculation", "data-transformation", "sandboxed-execution"],
            "local": True,
            "stateless": True,
            "sandboxed": True,
            "risk_level": "high",
            "data_access": "none",
            "output_freshness": "runtime_generated",
            "audit_level": "elevated",
        },
        "authorization_policy": _DEFAULT_MCP_AUTHORIZATION_POLICY,
        "enabled": True,
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
        if current_spec != spec:
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
        latest = find_registry_entity(database_url, entity_type="tool", entity_id=entity_id)
        upsert_tool_runtime_status(
            database_url,
            tool_id=entity_id,
            validated_version=str((latest or {}).get("current_version") or "v1"),
            last_validation_status="success",
            validation_errors=[],
        )
    for entity_id, spec in _BUILTIN_MCP_SERVERS.items():
        existing = find_registry_entity(database_url, entity_type="mcp_server", entity_id=entity_id)
        if existing is None:
            create_registry_entity(
                database_url,
                entity_id=entity_id,
                entity_type="mcp_server",
                owner_user_id=owner_user_id,
                visibility="private",
                status="published",
            )
            create_registry_version(
                database_url,
                entity_id=entity_id,
                version="v1",
                spec_json=dict(spec),
                set_current=True,
                published=True,
            )
        elif existing.get("current_version") is None:
            create_registry_version(
                database_url,
                entity_id=entity_id,
                version="v1",
                spec_json=dict(spec),
                set_current=True,
                published=True,
            )
        else:
            current_spec = existing.get("current_spec") if isinstance(existing.get("current_spec"), dict) else {}
            if current_spec != spec:
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
        latest = find_registry_entity(database_url, entity_type="mcp_server", entity_id=entity_id)
        upsert_mcp_server_status(
            database_url,
            mcp_server_id=entity_id,
            validated_version=str((latest or {}).get("current_version") or "v1"),
            runtime_status="success",
            validation_errors=[],
        )
    return True
