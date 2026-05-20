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
    "tool.image_license_plate_recognition": {
        "name": "License Plate Recognition",
        "description": "Finds license plates in an image and reads their text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "object",
                    "properties": {"data_base64": {"type": "string"}, "mime_type": {"type": "string"}},
                    "required": ["data_base64", "mime_type"],
                    "additionalProperties": False,
                },
                "options": {"type": "object", "additionalProperties": True},
            },
            "required": ["image"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object", "additionalProperties": True},
        "safety_policy": {"timeout_seconds": 30, "network_access": False},
        "offline_compatible": True,
        "execution_backend": "image_analysis",
        "transport": "image_analysis_http",
        "execution_config": {"tasks": ["license_plate_recognition"]},
        "permissions": {},
    },
    "tool.image_object_detection": {
        "name": "Object Detection",
        "description": "Detects objects and bounding boxes in an image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "object",
                    "properties": {"data_base64": {"type": "string"}, "mime_type": {"type": "string"}},
                    "required": ["data_base64", "mime_type"],
                    "additionalProperties": False,
                },
                "options": {"type": "object", "additionalProperties": True},
            },
            "required": ["image"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object", "additionalProperties": True},
        "safety_policy": {"timeout_seconds": 30, "network_access": False},
        "offline_compatible": True,
        "execution_backend": "image_analysis",
        "transport": "image_analysis_http",
        "execution_config": {"tasks": ["object_detection"]},
        "permissions": {},
    },
    "tool.image_captioning": {
        "name": "Image Captioning",
        "description": "Produces a text caption for an image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "object",
                    "properties": {"data_base64": {"type": "string"}, "mime_type": {"type": "string"}},
                    "required": ["data_base64", "mime_type"],
                    "additionalProperties": False,
                },
                "options": {"type": "object", "additionalProperties": True},
            },
            "required": ["image"],
            "additionalProperties": False,
        },
        "output_schema": {"type": "object", "additionalProperties": True},
        "safety_policy": {"timeout_seconds": 30, "network_access": False},
        "offline_compatible": True,
        "execution_backend": "image_analysis",
        "transport": "image_analysis_http",
        "execution_config": {"tasks": ["captioning"]},
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
    "mcp.image_license_plate_recognition": {
        "name": "License Plate Recognition",
        "slug": "image_license_plate_recognition",
        "description": "Expose the local license plate recognition tool.",
        "backing_tool_id": "tool.image_license_plate_recognition",
        "exposed_tool_name": "image_license_plate_recognition",
        "input_schema": _BUILTIN_TOOLS["tool.image_license_plate_recognition"]["input_schema"],
        "output_schema": _BUILTIN_TOOLS["tool.image_license_plate_recognition"]["output_schema"],
        "metadata": {
            "category": "data_analysis",
            "capabilities": ["image-analysis", "license-plate-recognition"],
            "local": True,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "user_data",
            "output_freshness": "runtime_generated",
            "audit_level": "standard",
        },
        "authorization_policy": _DEFAULT_MCP_AUTHORIZATION_POLICY,
        "enabled": True,
    },
    "mcp.image_object_detection": {
        "name": "Object Detection",
        "slug": "image_object_detection",
        "description": "Expose the local object detection tool.",
        "backing_tool_id": "tool.image_object_detection",
        "exposed_tool_name": "image_object_detection",
        "input_schema": _BUILTIN_TOOLS["tool.image_object_detection"]["input_schema"],
        "output_schema": _BUILTIN_TOOLS["tool.image_object_detection"]["output_schema"],
        "metadata": {
            "category": "data_analysis",
            "capabilities": ["image-analysis", "object-detection"],
            "local": True,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "user_data",
            "output_freshness": "runtime_generated",
            "audit_level": "standard",
        },
        "authorization_policy": _DEFAULT_MCP_AUTHORIZATION_POLICY,
        "enabled": True,
    },
    "mcp.image_captioning": {
        "name": "Image Captioning",
        "slug": "image_captioning",
        "description": "Expose the local image captioning tool.",
        "backing_tool_id": "tool.image_captioning",
        "exposed_tool_name": "image_captioning",
        "input_schema": _BUILTIN_TOOLS["tool.image_captioning"]["input_schema"],
        "output_schema": _BUILTIN_TOOLS["tool.image_captioning"]["output_schema"],
        "metadata": {
            "category": "data_analysis",
            "capabilities": ["image-analysis", "image-captioning"],
            "local": True,
            "stateless": True,
            "sandboxed": False,
            "risk_level": "medium",
            "data_access": "user_data",
            "output_freshness": "runtime_generated",
            "audit_level": "standard",
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
