from __future__ import annotations

from datetime import datetime, timezone
import re
from time import monotonic
from typing import Any, Literal

try:
    from jsonschema import Draft202012Validator, SchemaError
except ModuleNotFoundError:  # pragma: no cover - dependency is declared, fallback keeps local tests runnable
    Draft202012Validator = None  # type: ignore[assignment]

    class SchemaError(ValueError):
        pass

from ..repositories.catalog_runtime import (
    get_mcp_server_status,
    get_tool_runtime_status,
    list_mcp_server_statuses,
    list_tool_runtime_statuses,
    list_user_group_ids,
    log_mcp_invocation,
    upsert_mcp_server_status,
    upsert_tool_runtime_status,
)
from ..repositories.model_access import find_model_definition
from ..repositories.registry import (
    create_registry_entity,
    create_registry_version,
    delete_registry_entity,
    find_registry_entity,
    list_registry_entities,
    update_registry_entity,
)
from .agent_prompt_defaults import (
    build_agent_system_prompt_preview,
    coerce_agent_runtime_prompts,
    default_agent_runtime_prompts,
    normalize_agent_runtime_prompts,
)
from .knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID
from .catalog_errors import CatalogError
from .catalog_execution_trace import build_catalog_tool_runtime_log
from .catalog_tool_backends import (
    TOOL_BACKEND_IMAGE_ANALYSIS as _TOOL_BACKEND_IMAGE_ANALYSIS,
    TOOL_BACKEND_IMAGE_GENERATION as _TOOL_BACKEND_IMAGE_GENERATION,
    TOOL_BACKEND_SANDBOX as _TOOL_BACKEND_SANDBOX,
    TOOL_BACKEND_WEB_SEARCH as _TOOL_BACKEND_WEB_SEARCH,
    VALID_TOOL_BACKENDS as _VALID_TOOL_BACKENDS,
    build_tool_creation_options,
    ensure_execution_config,
    execute_backend,
    image_analysis_available_tasks,
    image_generation_available_tasks,
    mcp_metadata_defaults_for_tool_spec,
    tool_execution_backend,
    validate_backend,
)
from .platform_service import resolve_mcp_runtime_adapter, resolve_sandbox_execution_adapter, resolve_web_search_adapter
from .platform_types import PlatformControlPlaneError
from .user_agent_types import (
    CHANNEL_TYPE_VANESSA_WEBAPP,
    INTERFACE_TYPE_CHAT,
    coerce_channel_type,
    coerce_interface_type,
    coerce_user_agent_type,
    normalize_workflow_definition,
    workflow_actions,
    workflow_mcp_server_slugs,
)

_ENTITY_TYPE_AGENT = "agent"
_ENTITY_TYPE_TOOL = "tool"
_ENTITY_TYPE_MCP_SERVER = "mcp_server"
_VALID_VISIBILITIES = {"private", "unlisted", "public"}
_VALID_MCP_METADATA_CATEGORIES = {
    "web_search",
    "knowledge_retrieval",
    "code_execution",
    "data_analysis",
    "creative_media",
    "automation",
    "communication",
    "custom",
}
_VALID_MCP_METADATA_RISK_LEVELS = {"low", "medium", "high"}
_VALID_MCP_METADATA_DATA_ACCESS = {"none", "public_web", "workspace", "user_data", "secrets_or_credentials"}
_VALID_MCP_METADATA_OUTPUT_FRESHNESS = {"static", "fresh", "runtime_generated"}
_VALID_MCP_METADATA_AUDIT_LEVELS = {"standard", "elevated"}
_VERSION_PATTERN = re.compile(r"^v(?P<number>\d+)$", re.IGNORECASE)
_PLATFORM_AGENT_IDS = {KNOWLEDGE_CHAT_AGENT_ID}
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def list_catalog_agents(database_url: str) -> list[dict[str, Any]]:
    return [
        _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_AGENT, database_url=database_url)
        for row in list_registry_entities(database_url, entity_type=_ENTITY_TYPE_AGENT)
    ]


def list_catalog_tools(database_url: str, *, config: Any | None = None) -> list[dict[str, Any]]:
    available_image_tasks = _available_image_analysis_tasks(database_url, config)
    available_image_generation_tasks = _available_image_generation_tasks(database_url, config)
    web_search_available = _web_search_available(database_url, config)
    return [
        _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_TOOL, database_url=database_url)
        for row in list_registry_entities(database_url, entity_type=_ENTITY_TYPE_TOOL)
        if _tool_visible_for_runtime(row, available_image_tasks, available_image_generation_tasks, web_search_available)
    ]


def list_catalog_mcp_servers(database_url: str, *, config: Any | None = None) -> list[dict[str, Any]]:
    available_image_tasks = _available_image_analysis_tasks(database_url, config)
    available_image_generation_tasks = _available_image_generation_tasks(database_url, config)
    web_search_available = _web_search_available(database_url, config)
    return [
        _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_MCP_SERVER, database_url=database_url)
        for row in list_registry_entities(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER)
        if _mcp_server_visible_for_runtime(database_url, row, available_image_tasks, available_image_generation_tasks, web_search_available)
    ]


def get_catalog_defaults() -> dict[str, Any]:
    return {
        "agent": {
            "runtime_prompts": default_agent_runtime_prompts(),
        },
    }


def _available_image_analysis_tasks(database_url: str, config: Any | None) -> set[str] | None:
    if config is None:
        return None
    return image_analysis_available_tasks(database_url, config)


def _available_image_generation_tasks(database_url: str, config: Any | None) -> set[str] | None:
    if config is None:
        return None
    return image_generation_available_tasks(database_url, config)


def _web_search_available(database_url: str, config: Any | None) -> bool | None:
    if config is None:
        return None
    if hasattr(config, "web_search_enabled") and not bool(getattr(config, "web_search_enabled")):
        return False
    try:
        adapter = resolve_web_search_adapter(database_url, config)
        health = adapter.health()
        return bool(health.get("reachable", False))
    except Exception:
        return False


def _configured_image_analysis_tasks(spec: dict[str, Any]) -> set[str]:
    execution_config = spec.get("execution_config") if isinstance(spec.get("execution_config"), dict) else {}
    tasks = execution_config.get("tasks") if isinstance(execution_config.get("tasks"), list) else []
    return {str(task).strip().lower() for task in tasks if str(task).strip()}


def _tool_visible_for_runtime(
    row: dict[str, Any],
    available_image_tasks: set[str] | None,
    available_image_generation_tasks: set[str] | None,
    web_search_available: bool | None,
) -> bool:
    if available_image_tasks is None and available_image_generation_tasks is None and web_search_available is None:
        return True
    spec = row.get("current_spec") if isinstance(row.get("current_spec"), dict) else {}
    execution_backend = tool_execution_backend(spec)
    if execution_backend == _TOOL_BACKEND_WEB_SEARCH:
        return web_search_available is not False
    if execution_backend == _TOOL_BACKEND_IMAGE_ANALYSIS:
        if available_image_tasks is None:
            return True
        configured_tasks = _configured_image_analysis_tasks(spec)
        if not configured_tasks:
            return bool(available_image_tasks)
        return configured_tasks <= available_image_tasks
    if execution_backend == _TOOL_BACKEND_IMAGE_GENERATION:
        if available_image_generation_tasks is None:
            return True
        configured_tasks = _configured_image_analysis_tasks(spec)
        if not configured_tasks:
            return bool(available_image_generation_tasks)
        return configured_tasks <= available_image_generation_tasks
    return True


def _mcp_server_visible_for_runtime(
    database_url: str,
    row: dict[str, Any],
    available_image_tasks: set[str] | None,
    available_image_generation_tasks: set[str] | None,
    web_search_available: bool | None,
) -> bool:
    if available_image_tasks is None and available_image_generation_tasks is None and web_search_available is None:
        return True
    spec = row.get("current_spec") if isinstance(row.get("current_spec"), dict) else {}
    backing_tool_id = str(spec.get("backing_tool_id") or "").strip()
    if not backing_tool_id:
        return True
    tool_row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=backing_tool_id)
    if tool_row is None:
        return True
    return _tool_visible_for_runtime(tool_row, available_image_tasks, available_image_generation_tasks, web_search_available)


def get_catalog_tool_creation_options(database_url: str, *, config: Any) -> dict[str, Any]:
    return build_tool_creation_options(database_url, config=config)


def get_catalog_mcp_creation_options(database_url: str, *, config: Any | None = None) -> dict[str, Any]:
    tools = list_catalog_tools(database_url, config=config) if config is not None else list_catalog_tools(database_url)
    return {
        "tools": [
            {
                "tool_id": tool["id"],
                "metadata_defaults": mcp_metadata_defaults_for_tool_spec(tool.get("spec") if isinstance(tool.get("spec"), dict) else {}),
            }
            for tool in tools
        ],
    }


def get_catalog_agent(database_url: str, *, agent_id: str) -> dict[str, Any]:
    row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=agent_id)
    if row is None:
        raise CatalogError("agent_not_found", "Agent not found", status_code=404)
    return _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_AGENT, database_url=database_url)


def get_catalog_tool(database_url: str, *, tool_id: str) -> dict[str, Any]:
    row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=tool_id)
    if row is None:
        raise CatalogError("tool_not_found", "Tool not found", status_code=404)
    return _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_TOOL, database_url=database_url)


def get_catalog_mcp_server(database_url: str, *, mcp_server_id: str) -> dict[str, Any]:
    row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER, entity_id=mcp_server_id)
    if row is None:
        raise CatalogError("mcp_server_not_found", "MCP server not found", status_code=404)
    return _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_MCP_SERVER, database_url=database_url)


def create_catalog_agent(
    database_url: str,
    *,
    payload: dict[str, Any],
    owner_user_id: int,
) -> dict[str, Any]:
    entity_id = str(payload.get("id", "")).strip()
    if not entity_id:
        raise CatalogError("invalid_agent_id", "id is required")
    if find_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=entity_id) is not None:
        raise CatalogError("duplicate_agent", "Agent already exists", status_code=409)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", "private"))
    spec = _coerce_agent_spec(payload)
    create_registry_entity(
        database_url,
        entity_id=entity_id,
        entity_type=_ENTITY_TYPE_AGENT,
        owner_user_id=owner_user_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    create_registry_version(
        database_url,
        entity_id=entity_id,
        version="v1",
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    return get_catalog_agent(database_url, agent_id=entity_id)


def update_catalog_agent(
    database_url: str,
    *,
    agent_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=agent_id)
    if existing is None:
        raise CatalogError("agent_not_found", "Agent not found", status_code=404)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", existing.get("visibility", "private")))
    spec = _coerce_agent_spec(payload)
    create_registry_version(
        database_url,
        entity_id=agent_id,
        version=_next_version(existing.get("current_version")),
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    update_registry_entity(
        database_url,
        entity_id=agent_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    return get_catalog_agent(database_url, agent_id=agent_id)


def delete_catalog_agent(
    database_url: str,
    *,
    agent_id: str,
    actor_user_id: int,
    actor_role: str,
) -> None:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=agent_id)
    if existing is None:
        raise CatalogError("agent_not_found", "Agent not found", status_code=404)
    if _is_platform_agent(agent_id):
        raise CatalogError(
            "platform_agent_delete_blocked",
            "Platform agents can be edited or deactivated, but not deleted.",
            status_code=409,
        )
    owner_user_id = existing.get("owner_user_id")
    if str(actor_role).strip().lower() != "superadmin" and int(owner_user_id or 0) != int(actor_user_id):
        raise CatalogError("agent_delete_forbidden", "Only the agent owner can delete this agent.", status_code=403)
    deleted = delete_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=agent_id)
    if not deleted:
        raise CatalogError("agent_not_found", "Agent not found", status_code=404)


def create_catalog_tool(
    database_url: str,
    *,
    payload: dict[str, Any],
    owner_user_id: int,
    config: Any | None = None,
) -> dict[str, Any]:
    entity_id = str(payload.get("id", "")).strip()
    if not entity_id:
        raise CatalogError("invalid_tool_id", "id is required")
    if find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=entity_id) is not None:
        raise CatalogError("duplicate_tool", "Tool already exists", status_code=409)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", "private"))
    spec = _coerce_tool_spec(database_url, payload, config=config)
    create_registry_entity(
        database_url,
        entity_id=entity_id,
        entity_type=_ENTITY_TYPE_TOOL,
        owner_user_id=owner_user_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    create_registry_version(
        database_url,
        entity_id=entity_id,
        version="v1",
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    return get_catalog_tool(database_url, tool_id=entity_id)


def update_catalog_tool(
    database_url: str,
    *,
    tool_id: str,
    payload: dict[str, Any],
    config: Any | None = None,
) -> dict[str, Any]:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=tool_id)
    if existing is None:
        raise CatalogError("tool_not_found", "Tool not found", status_code=404)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", existing.get("visibility", "private")))
    spec = _coerce_tool_spec(database_url, payload, config=config)
    create_registry_version(
        database_url,
        entity_id=tool_id,
        version=_next_version(existing.get("current_version")),
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    update_registry_entity(
        database_url,
        entity_id=tool_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    return get_catalog_tool(database_url, tool_id=tool_id)


def create_catalog_mcp_server(
    database_url: str,
    *,
    payload: dict[str, Any],
    owner_user_id: int,
) -> dict[str, Any]:
    entity_id = str(payload.get("id") or f"mcp.{payload.get('slug', '')}").strip()
    if not entity_id:
        raise CatalogError("invalid_mcp_server_id", "id or slug is required")
    if find_registry_entity(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER, entity_id=entity_id) is not None:
        raise CatalogError("duplicate_mcp_server", "MCP server already exists", status_code=409)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", "private"))
    spec = _coerce_mcp_server_spec(database_url, payload, current_id=None)
    create_registry_entity(
        database_url,
        entity_id=entity_id,
        entity_type=_ENTITY_TYPE_MCP_SERVER,
        owner_user_id=owner_user_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    create_registry_version(
        database_url,
        entity_id=entity_id,
        version="v1",
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    return get_catalog_mcp_server(database_url, mcp_server_id=entity_id)


def update_catalog_mcp_server(
    database_url: str,
    *,
    mcp_server_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER, entity_id=mcp_server_id)
    if existing is None:
        raise CatalogError("mcp_server_not_found", "MCP server not found", status_code=404)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", existing.get("visibility", "private")))
    spec = _coerce_mcp_server_spec(database_url, payload, current_id=mcp_server_id)
    create_registry_version(
        database_url,
        entity_id=mcp_server_id,
        version=_next_version(existing.get("current_version")),
        spec_json=spec,
        set_current=True,
        published=publish,
    )
    update_registry_entity(
        database_url,
        entity_id=mcp_server_id,
        visibility=visibility,
        status=_entity_status(publish),
    )
    return get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)


def delete_catalog_mcp_server(database_url: str, *, mcp_server_id: str) -> None:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER, entity_id=mcp_server_id)
    if existing is None:
        raise CatalogError("mcp_server_not_found", "MCP server not found", status_code=404)
    deleted = delete_registry_entity(database_url, entity_type=_ENTITY_TYPE_MCP_SERVER, entity_id=mcp_server_id)
    if not deleted:
        raise CatalogError("mcp_server_not_found", "MCP server not found", status_code=404)


def set_catalog_mcp_server_enabled(
    database_url: str,
    *,
    mcp_server_id: str,
    enabled: bool,
) -> dict[str, Any]:
    server = get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)
    payload = {
        **server["spec"],
        "id": server["id"],
        "visibility": server["entity"]["visibility"],
        "publish": server["published"],
        "enabled": enabled,
    }
    return update_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id, payload=payload)


def validate_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
) -> dict[str, Any]:
    tool = get_catalog_tool(database_url, tool_id=tool_id)
    spec = dict(tool["spec"])
    runtime_checks, errors = _validate_catalog_tool_definition(
        database_url=database_url,
        config=config,
        spec=spec,
    )
    warnings: list[str] = []
    validation_status = "success" if not errors else "failed"
    try:
        upsert_tool_runtime_status(
            database_url,
            tool_id=tool_id,
            validated_version=str(tool.get("current_version") or ""),
            last_validation_status=validation_status,
            validation_errors=errors,
        )
    except Exception:
        pass
    tool = get_catalog_tool(database_url, tool_id=tool_id)

    return {
        "tool": tool,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "runtime_checks": runtime_checks,
        },
    }


def validate_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    mcp_server_id: str,
) -> dict[str, Any]:
    server = get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)
    runtime_checks, errors = _validate_mcp_server_definition(
        database_url=database_url,
        config=config,
        spec=dict(server["spec"]),
    )
    runtime_status = "success" if not errors else "failed"
    upsert_mcp_server_status(
        database_url,
        mcp_server_id=mcp_server_id,
        validated_version=str(server.get("current_version") or ""),
        runtime_status=runtime_status,
        validation_errors=errors,
    )
    server = get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)
    return {
        "mcp_server": server,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": [],
            "runtime_checks": runtime_checks,
        },
    }


def execute_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
    payload: dict[str, Any],
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    tool = get_catalog_tool(database_url, tool_id=tool_id)
    spec = dict(tool["spec"])
    tool_input = payload.get("input")
    if not isinstance(tool_input, dict):
        raise CatalogError("invalid_tool_input", "input must be a JSON object")

    request_metadata = payload.get("request_metadata") if isinstance(payload.get("request_metadata"), dict) else {}
    if actor_user_id is not None and "actor_user_id" not in request_metadata:
        request_metadata = {**request_metadata, "actor_user_id": actor_user_id}

    started_at = datetime.now(timezone.utc)
    started_monotonic = monotonic()
    result_payload, status_code = _execute_internal_tool(
        database_url=database_url,
        config=config,
        tool_id=tool_id,
        spec=spec,
        tool_input=tool_input,
        request_metadata=request_metadata,
    )
    completed_at = datetime.now(timezone.utc)
    return _serialize_catalog_tool_execution(
        tool=tool,
        input_payload=tool_input,
        request_metadata=request_metadata,
        result_payload=result_payload,
        status_code=status_code,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, int(round((monotonic() - started_monotonic) * 1000))),
    )


def test_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    mcp_server_id: str,
    payload: dict[str, Any],
    actor_user_id: int | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    server = get_catalog_mcp_server(database_url, mcp_server_id=mcp_server_id)
    arguments = payload.get("arguments", payload.get("input", {}))
    if not isinstance(arguments, dict):
        raise CatalogError("invalid_mcp_arguments", "arguments must be a JSON object")
    request_metadata = payload.get("request_metadata") if isinstance(payload.get("request_metadata"), dict) else {}
    if actor_user_id is not None:
        request_metadata = {
            **request_metadata,
            "agent_id": request_metadata.get("agent_id") or "catalog.superadmin.test",
            "delegated_user_id": actor_user_id,
            "delegated_user_role": actor_role or "superadmin",
            "agent_domain": request_metadata.get("agent_domain") or "default",
        }
    result_payload, status_code = invoke_catalog_mcp_server(
        database_url,
        config=config,
        slug=str(server["spec"]["slug"]),
        arguments=arguments,
        request_metadata=request_metadata,
    )
    return {
        "mcp_server": server,
        "execution": {
            "arguments": arguments,
            "request_metadata": request_metadata,
            "status_code": status_code,
            "ok": result_payload is not None and 200 <= status_code < 300 and not result_payload.get("error"),
            "result": result_payload.get("result") if isinstance(result_payload, dict) else None,
            "error": result_payload.get("error") if isinstance(result_payload, dict) else None,
        },
    }


def discover_authorized_mcp_servers(
    database_url: str,
    *,
    config: Any | None = None,
    agent_id: str | None,
    agent_domain: str | None,
    delegated_user_id: int | None,
    delegated_user_role: str | None,
) -> list[dict[str, Any]]:
    user_group_ids = list_user_group_ids(database_url, user_id=delegated_user_id) if delegated_user_id else set()
    discovered: list[dict[str, Any]] = []
    servers = list_catalog_mcp_servers(database_url, config=config) if config is not None else list_catalog_mcp_servers(database_url)
    for server in servers:
        spec = server.get("spec") if isinstance(server.get("spec"), dict) else {}
        if not bool(spec.get("enabled", False)):
            continue
        if not _mcp_policy_allows(
            spec.get("authorization_policy") if isinstance(spec.get("authorization_policy"), dict) else {},
            agent_id=agent_id,
            agent_domain=agent_domain,
            delegated_user_id=delegated_user_id,
            delegated_user_role=delegated_user_role,
            user_group_ids=user_group_ids,
        ):
            continue
        discovered.append(
            {
                "id": server["id"],
                "slug": spec.get("slug"),
                "tool_name": spec.get("exposed_tool_name"),
                "description": spec.get("description"),
                "input_schema": spec.get("input_schema"),
                "output_schema": spec.get("output_schema"),
                "backing_tool_id": spec.get("backing_tool_id"),
                "metadata": spec.get("metadata"),
                "enabled": spec.get("enabled"),
                "updated_at": server.get("published_at"),
            }
        )
    return discovered


def invoke_catalog_mcp_server(
    database_url: str,
    *,
    config: Any,
    slug: str,
    arguments: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    started_at = monotonic()
    server = _find_mcp_server_by_slug(database_url, slug)
    server_id = server["id"] if server is not None else None
    backing_tool_id: str | None = None
    status = "failed"
    status_code = 500
    error: dict[str, Any] | None = None
    try:
        if server is None:
            raise CatalogError("mcp_server_not_found", "MCP server not found", status_code=404)
        spec = server.get("spec") if isinstance(server.get("spec"), dict) else {}
        if not bool(spec.get("enabled", False)):
            raise CatalogError("mcp_server_disabled", "MCP server is disabled", status_code=403)
        backing_tool_id = str(spec.get("backing_tool_id", "")).strip()
        agent_id = _metadata_string(request_metadata, "agent_id")
        agent_domain = _metadata_string(request_metadata, "agent_domain") or "default"
        delegated_user_id = _metadata_int(request_metadata, "delegated_user_id")
        delegated_user_role = _metadata_string(request_metadata, "delegated_user_role")
        user_group_ids = list_user_group_ids(database_url, user_id=delegated_user_id) if delegated_user_id else set()
        if not _mcp_policy_allows(
            spec.get("authorization_policy") if isinstance(spec.get("authorization_policy"), dict) else {},
            agent_id=agent_id,
            agent_domain=agent_domain,
            delegated_user_id=delegated_user_id,
            delegated_user_role=delegated_user_role,
            user_group_ids=user_group_ids,
        ):
            raise CatalogError("mcp_server_forbidden", "MCP server is not authorized for this agent or user", status_code=403)
        input_errors = _validate_json_payload(dict(spec.get("input_schema") or {}), arguments, field_name="input")
        if input_errors:
            raise CatalogError("invalid_mcp_arguments", "MCP arguments do not match schema", details={"errors": input_errors})
        tool = get_catalog_tool(database_url, tool_id=backing_tool_id)
        available_image_tasks = _available_image_analysis_tasks(database_url, config)
        available_image_generation_tasks = _available_image_generation_tasks(database_url, config)
        web_search_available = _web_search_available(database_url, config)
        if not _tool_visible_for_runtime(
            {
                "current_spec": tool.get("spec") if isinstance(tool.get("spec"), dict) else {},
            },
            available_image_tasks,
            available_image_generation_tasks,
            web_search_available,
        ):
            raise CatalogError("mcp_server_unavailable", "MCP server backing tool is unavailable for the active runtime providers", status_code=409)
        result_payload, status_code = _execute_internal_tool(
            database_url=database_url,
            config=config,
            tool_id=backing_tool_id,
            spec=dict(tool["spec"]),
            tool_input=arguments,
            request_metadata=request_metadata,
        )
        if result_payload is None:
            result_payload = {"error": "tool_runtime_unavailable", "message": "Tool runtime unavailable"}
        if 200 <= status_code < 300 and not result_payload.get("error"):
            output_errors = _validate_json_payload(dict(spec.get("output_schema") or {}), result_payload, field_name="output")
            if output_errors:
                result_payload = {"error": "invalid_mcp_output", "message": "MCP output does not match schema", "details": {"errors": output_errors}}
                status_code = 502
        status = "success" if 200 <= status_code < 300 and not result_payload.get("error") else "failed"
        error = result_payload.get("error") if isinstance(result_payload.get("error"), dict) else (
            {"error": result_payload.get("error")} if result_payload.get("error") else None
        )
        return {
            "tool_name": spec.get("exposed_tool_name"),
            "server_slug": spec.get("slug"),
            "arguments": arguments,
            "request_metadata": request_metadata,
            "result": result_payload if status == "success" else None,
            "error": result_payload if status != "success" else None,
        }, status_code
    except CatalogError as exc:
        status_code = exc.status_code
        error = {"error": exc.code, "message": exc.message, "details": exc.details or {}}
        return {"error": error, "result": None}, status_code
    finally:
        try:
            log_mcp_invocation(
                database_url,
                mcp_server_id=server_id,
                mcp_server_slug=str(slug),
                backing_tool_id=backing_tool_id,
                agent_id=_metadata_string(request_metadata, "agent_id"),
                agent_domain=_metadata_string(request_metadata, "agent_domain"),
                delegated_user_id=_metadata_int(request_metadata, "delegated_user_id"),
                delegated_user_role=_metadata_string(request_metadata, "delegated_user_role"),
                status=status,
                status_code=status_code,
                error=error,
                duration_ms=int((monotonic() - started_at) * 1000),
                request_metadata=request_metadata,
            )
        except Exception:
            pass


def validate_catalog_agent(database_url: str, *, agent_id: str) -> dict[str, Any]:
    agent = get_catalog_agent(database_url, agent_id=agent_id)
    spec = dict(agent["spec"])
    errors: list[str] = []
    warnings: list[str] = []
    default_model_ref = spec.get("default_model_ref")
    if default_model_ref is not None and str(default_model_ref).strip():
        if find_model_definition(database_url, str(default_model_ref).strip()) is None:
            errors.append(f"Model '{default_model_ref}' does not exist.")

    resolved_tools: list[dict[str, Any]] = []
    resolved_mcp_servers: list[dict[str, Any]] = []
    derived_runtime_requirements = {
        "internet_required": False,
        "sandbox_required": False,
    }

    for tool_ref in spec.get("tool_refs", []):
        tool_id = str(tool_ref).strip()
        tool_row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=tool_id)
        if tool_row is None:
            errors.append(f"Tool '{tool_id}' does not exist.")
            continue
        tool = _serialize_catalog_row(tool_row, entity_type=_ENTITY_TYPE_TOOL, database_url=database_url)
        tool_spec = dict(tool["spec"])
        execution_backend = _tool_execution_backend(tool_spec)
        offline_compatible = bool(tool_spec.get("offline_compatible", False))
        resolved_tools.append(
            {
                "id": tool["id"],
                "name": tool_spec.get("name"),
                "execution_backend": execution_backend,
                "offline_compatible": offline_compatible,
            }
        )
        if execution_backend == _TOOL_BACKEND_SANDBOX:
            derived_runtime_requirements["sandbox_required"] = True
        if not offline_compatible:
            derived_runtime_requirements["internet_required"] = True

    configured_mcp_refs = {str(value).strip() for value in spec.get("mcp_server_refs", []) if str(value).strip()}
    workflow_definition = spec.get("workflow_definition") if isinstance(spec.get("workflow_definition"), dict) else {}
    workflow_mcp_refs = set(workflow_mcp_server_slugs(workflow_definition))
    for slug in sorted(configured_mcp_refs | workflow_mcp_refs):
        if not slug:
            continue
        mcp_server = _find_mcp_server_by_slug(database_url, slug)
        if mcp_server is None:
            errors.append(f"MCP server '{slug}' does not exist.")
            continue
        mcp_spec = dict(mcp_server["spec"])
        backing_tool = get_catalog_tool(database_url, tool_id=str(mcp_spec.get("backing_tool_id", "")))
        tool_spec = dict(backing_tool["spec"])
        resolved_mcp_servers.append(
            {
                "id": mcp_server["id"],
                "slug": mcp_spec.get("slug"),
                "name": mcp_spec.get("name"),
                "backing_tool_id": backing_tool["id"],
                "enabled": bool(mcp_spec.get("enabled", False)),
                "metadata": mcp_spec.get("metadata"),
            }
        )
        if _tool_execution_backend(tool_spec) == _TOOL_BACKEND_SANDBOX:
            derived_runtime_requirements["sandbox_required"] = True
        if not bool(tool_spec.get("offline_compatible", False)):
            derived_runtime_requirements["internet_required"] = True
        if not bool(mcp_spec.get("enabled", False)):
            errors.append(f"MCP server '{slug}' is disabled.")

    runtime_constraints = spec.get("runtime_constraints") if isinstance(spec.get("runtime_constraints"), dict) else {}
    if spec.get("agent_type") == "workflow":
        actions = workflow_actions(workflow_definition)
        if not actions:
            errors.append("Workflow agents require at least one workflow action.")
        elif str(actions[0].get("type") or "") != "get_user_input" or str(actions[-1].get("type") or "") != "send_output":
            errors.append("Workflow agents must start with get_user_input and end with send_output.")
    if spec.get("channel_type") == CHANNEL_TYPE_VANESSA_WEBAPP and spec.get("interface_type") != INTERFACE_TYPE_CHAT:
        errors.append("channel_type vanessa_webapp currently requires interface_type chat.")
    if derived_runtime_requirements["sandbox_required"] and not bool(runtime_constraints.get("sandbox_required", False)):
        errors.append("Agent references sandbox tools but runtime_constraints.sandbox_required is false.")
    if derived_runtime_requirements["internet_required"] and not bool(runtime_constraints.get("internet_required", False)):
        errors.append("Agent references online-only tools but runtime_constraints.internet_required is false.")

    return {
        "agent": agent,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "resolved_tools": resolved_tools,
            "resolved_mcp_servers": resolved_mcp_servers,
            "derived_runtime_requirements": derived_runtime_requirements,
        },
    }


def preview_catalog_agent_prompt(database_url: str, *, agent_id: str) -> dict[str, Any]:
    agent = get_catalog_agent(database_url, agent_id=agent_id)
    return {
        "agent": agent,
        "prompt_preview": build_agent_system_prompt_preview(dict(agent["spec"])),
    }


def preview_catalog_agent_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    agent_type = str(payload.get("agent_type") or "workflow").strip() or "workflow"
    spec = {
        "agent_type": agent_type,
        "instructions": str(payload.get("instructions") or ""),
        "runtime_prompts": normalize_agent_runtime_prompts(
            payload.get("runtime_prompts"),
            agent_type=agent_type,
        ),
        "workflow_definition": normalize_workflow_definition(payload.get("workflow_definition")),
    }
    return {"prompt_preview": build_agent_system_prompt_preview(spec)}


def _serialize_catalog_row(
    row: dict[str, Any],
    *,
    entity_type: Literal["agent", "tool", "mcp_server"],
    database_url: str,
) -> dict[str, Any]:
    current_spec = row.get("current_spec") if isinstance(row.get("current_spec"), dict) else {}
    if entity_type == _ENTITY_TYPE_AGENT:
        current_spec = _normalize_agent_spec_for_response(current_spec)
    if entity_type == _ENTITY_TYPE_MCP_SERVER:
        current_spec = _normalize_mcp_server_spec_for_response(current_spec)
    published = row.get("published_at") is not None
    serialized = {
        "id": str(row.get("entity_id", "")),
        "entity": {
            "id": str(row.get("entity_id", "")),
            "type": entity_type,
            "owner_user_id": row.get("owner_user_id"),
            "visibility": str(row.get("visibility", "private")),
        },
        "current_version": str(row.get("current_version", "") or ""),
        "status": str(row.get("status", _entity_status(published))),
        "published": published,
        "published_at": row.get("published_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "spec": current_spec,
    }
    if entity_type == _ENTITY_TYPE_AGENT:
        serialized["agent_kind"] = "platform" if _is_platform_agent(str(row.get("entity_id", ""))) else "user"
        serialized["is_platform_agent"] = serialized["agent_kind"] == "platform"
    if entity_type == _ENTITY_TYPE_TOOL:
        try:
            status = get_tool_runtime_status(database_url, tool_id=serialized["id"])
        except Exception:
            status = None
        serialized["validation_status"] = _serialize_tool_validation_status(status, serialized["current_version"])
    if entity_type == _ENTITY_TYPE_MCP_SERVER:
        status = None
        try:
            status = get_mcp_server_status(database_url, mcp_server_id=serialized["id"])
        except Exception:
            status = None
        serialized["validation_status"] = _serialize_mcp_validation_status(status, serialized["current_version"])
    return serialized


def _is_platform_agent(agent_id: str) -> bool:
    return str(agent_id).strip() in _PLATFORM_AGENT_IDS


def _normalize_agent_spec_for_response(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(spec)
    normalized["agent_type"] = str(normalized.get("agent_type") or "workflow").strip() or "workflow"
    normalized["runtime_prompts"] = normalize_agent_runtime_prompts(
        normalized.get("runtime_prompts"),
        agent_type=normalized["agent_type"],
    )
    normalized["agent_domain"] = str(normalized.get("agent_domain") or "default").strip() or "default"
    normalized["channel_type"] = str(normalized.get("channel_type") or CHANNEL_TYPE_VANESSA_WEBAPP).strip() or CHANNEL_TYPE_VANESSA_WEBAPP
    normalized["interface_type"] = str(normalized.get("interface_type") or INTERFACE_TYPE_CHAT).strip() or INTERFACE_TYPE_CHAT
    normalized["tool_refs"] = list(normalized.get("tool_refs") or [])
    normalized["mcp_server_refs"] = list(normalized.get("mcp_server_refs") or [])
    normalized["workflow_definition"] = normalize_workflow_definition(normalized.get("workflow_definition"))
    return normalized


def _normalize_mcp_server_spec_for_response(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(spec)
    normalized["metadata"] = _coerce_mcp_metadata(normalized.get("metadata"), require_all=False)
    return normalized


def _serialize_tool_validation_status(status: dict[str, Any] | None, current_version: str) -> dict[str, Any]:
    status = status if isinstance(status, dict) else {}
    validated_version = str(status.get("validated_version") or "")
    return {
        "last_validation_status": str(status.get("last_validation_status") or "unknown"),
        "is_validation_current": bool(validated_version and validated_version == str(current_version or "")),
        "validated_version": validated_version or None,
        "last_validated_at": status.get("last_validated_at"),
        "validation_errors": list(status.get("validation_errors") or []),
    }


def _serialize_mcp_validation_status(status: dict[str, Any] | None, current_version: str) -> dict[str, Any]:
    status = status if isinstance(status, dict) else {}
    validated_version = str(status.get("validated_version") or "")
    return {
        "last_validation_status": str(status.get("runtime_status") or "unknown"),
        "is_validation_current": bool(validated_version and validated_version == str(current_version or "")),
        "validated_version": validated_version or None,
        "last_validated_at": status.get("last_validated_at"),
        "validation_errors": list(status.get("validation_errors") or []),
    }


def _find_mcp_server_by_slug(database_url: str, slug: str) -> dict[str, Any] | None:
    normalized_slug = str(slug).strip().lower()
    if not normalized_slug:
        return None
    for server in list_catalog_mcp_servers(database_url):
        spec = server.get("spec") if isinstance(server.get("spec"), dict) else {}
        if str(spec.get("slug", "")).strip().lower() == normalized_slug:
            return server
    return None


def _validate_catalog_tool_definition(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    runtime_checks: dict[str, Any] = {
        "execution_backend": _tool_execution_backend(spec),
        "provider_reachable": False,
    }
    input_schema = spec.get("input_schema") if isinstance(spec.get("input_schema"), dict) else {}
    output_schema = spec.get("output_schema") if isinstance(spec.get("output_schema"), dict) else {}
    try:
        _validate_json_schema(input_schema, field_name="input_schema")
        _validate_json_schema(output_schema, field_name="output_schema")
    except CatalogError as exc:
        errors.append(exc.message)

    validate_backend(database_url=database_url, config=config, spec=spec, runtime_checks=runtime_checks, errors=errors)
    return runtime_checks, errors


def _validate_mcp_server_definition(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    runtime_checks: dict[str, Any] = {
        "mcp_runtime_reachable": False,
        "backing_tool_eligible": False,
    }
    try:
        _ensure_tool_eligible_for_mcp(database_url, tool_id=str(spec.get("backing_tool_id", "")))
        runtime_checks["backing_tool_eligible"] = True
    except CatalogError as exc:
        errors.append(exc.message)
    for field_name in ["input_schema", "output_schema"]:
        schema = spec.get(field_name)
        if not isinstance(schema, dict):
            errors.append(f"{field_name} must be an object")
            continue
        try:
            _validate_json_schema(schema, field_name=field_name)
        except CatalogError as exc:
            errors.append(exc.message)
    try:
        adapter = resolve_mcp_runtime_adapter(database_url, config)
        health = adapter.health()
        runtime_checks["mcp_runtime_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        if not runtime_checks["mcp_runtime_reachable"]:
            errors.append("MCP runtime provider is not reachable.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code
    return runtime_checks, errors


def _runtime_capability_for_transport(transport: str) -> str:
    if transport == "mcp":
        return "mcp_runtime"
    if transport == "sandbox_http":
        return "sandbox_execution"
    return "unknown"


def _validate_catalog_tool_transport(
    *,
    database_url: str,
    config: Any,
    transport: str,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    runtime_checks: dict[str, Any] = {
        "runtime_capability": _runtime_capability_for_transport(transport),
        "provider_reachable": False,
        "provider_status_code": None,
    }
    errors: list[str] = []

    if transport == "mcp":
        _validate_mcp_tool_transport(
            database_url=database_url,
            config=config,
            spec=spec,
            runtime_checks=runtime_checks,
            errors=errors,
        )
        return runtime_checks, errors

    if transport == "sandbox_http":
        _validate_sandbox_tool_transport(
            database_url=database_url,
            config=config,
            spec=spec,
            runtime_checks=runtime_checks,
            errors=errors,
        )
        return runtime_checks, errors

    errors.append(f"Unsupported transport '{transport}'.")
    return runtime_checks, errors


def _validate_mcp_tool_transport(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    try:
        adapter = resolve_mcp_runtime_adapter(database_url, config)
        health = adapter.health()
        runtime_checks["provider_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        tools_payload, status_code = adapter.list_tools()
        runtime_checks["tools_status_code"] = status_code
        tools = tools_payload.get("tools") if isinstance(tools_payload, dict) else []
        available_names = {
            str(item.get("tool_name", "")).strip()
            for item in tools
            if isinstance(item, dict) and str(item.get("tool_name", "")).strip()
        }
        expected_name = str(spec.get("tool_name", "")).strip()
        runtime_checks["tool_discovered"] = expected_name in available_names
        runtime_checks["available_tool_names"] = sorted(available_names)
        if not runtime_checks["provider_reachable"]:
            errors.append("MCP runtime provider is not reachable.")
        if not runtime_checks["tool_discovered"]:
            errors.append(f"MCP gateway does not expose tool '{expected_name}'.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code
        runtime_checks["tool_discovered"] = False


def _validate_sandbox_tool_transport(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    runtime_checks: dict[str, Any],
    errors: list[str],
) -> None:
    try:
        adapter = resolve_sandbox_execution_adapter(database_url, config)
        health = adapter.health()
        runtime_checks["provider_reachable"] = bool(health.get("reachable", False))
        runtime_checks["provider_status_code"] = health.get("status_code")
        safety_policy = spec.get("safety_policy") if isinstance(spec.get("safety_policy"), dict) else {}
        dry_run_payload, dry_run_status = adapter.execute(
            code=str(safety_policy.get("dry_run_code", "result = {'status': 'ok'}")),
            language="python",
            input_payload={},
            timeout_seconds=int(safety_policy.get("timeout_seconds", 5) or 5),
            policy=safety_policy,
        )
        dry_run_ok = dry_run_payload is not None and 200 <= dry_run_status < 300 and not dry_run_payload.get("error")
        runtime_checks["sandbox_dry_run_ok"] = dry_run_ok
        runtime_checks["sandbox_dry_run_status_code"] = dry_run_status
        if not runtime_checks["provider_reachable"]:
            errors.append("Sandbox runtime provider is not reachable.")
        if not dry_run_ok:
            errors.append("Sandbox dry-run execution failed.")
    except PlatformControlPlaneError as exc:
        errors.append(exc.message)
        runtime_checks["provider_status_code"] = exc.status_code
        runtime_checks["sandbox_dry_run_ok"] = False


def _execute_catalog_tool_transport(
    *,
    database_url: str,
    config: Any,
    transport: str,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    if transport == "mcp":
        return _execute_mcp_tool_transport(
            database_url=database_url,
            config=config,
            spec=spec,
            tool_input=tool_input,
            request_metadata=request_metadata,
        )

    if transport == "sandbox_http":
        return _execute_sandbox_tool_transport(
            database_url=database_url,
            config=config,
            spec=spec,
            tool_input=tool_input,
        )

    raise CatalogError("invalid_transport", f"Unsupported transport '{transport}'.")


def _execute_internal_tool(
    *,
    database_url: str,
    config: Any,
    tool_id: str,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    input_schema = spec.get("input_schema") if isinstance(spec.get("input_schema"), dict) else {}
    input_errors = _validate_json_payload(input_schema, tool_input, field_name="input")
    if input_errors:
        raise CatalogError("invalid_tool_input", "Tool input does not match schema", details={"errors": input_errors})

    result_payload, status_code = execute_backend(
        database_url=database_url,
        config=config,
        spec=spec,
        tool_input=tool_input,
        request_metadata=request_metadata,
    )

    payload = result_payload if isinstance(result_payload, dict) else {}
    if 200 <= status_code < 300 and not payload.get("error"):
        output_schema = spec.get("output_schema") if isinstance(spec.get("output_schema"), dict) else {}
        output_errors = _validate_json_payload(output_schema, payload, field_name="output")
        if output_errors:
            return {"error": "invalid_tool_output", "message": "Tool output does not match schema", "details": {"errors": output_errors}}, 502
    return result_payload, status_code


def _execute_mcp_tool_transport(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    try:
        adapter = resolve_mcp_runtime_adapter(database_url, config)
        return adapter.invoke(
            tool_name=str(spec.get("tool_name", "")).strip(),
            arguments=tool_input,
            request_metadata=request_metadata,
        )
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc


def _execute_sandbox_tool_transport(
    *,
    database_url: str,
    config: Any,
    spec: dict[str, Any],
    tool_input: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    code = str(tool_input.get("code", "")).strip()
    if not code:
        raise CatalogError("invalid_tool_input", "Sandbox tools require input.code")
    safety_policy = spec.get("safety_policy") if isinstance(spec.get("safety_policy"), dict) else {}
    timeout_seconds = int(tool_input.get("timeout_seconds") or safety_policy.get("timeout_seconds") or 5)
    language = str(tool_input.get("language", "python")).strip() or "python"
    try:
        adapter = resolve_sandbox_execution_adapter(database_url, config)
        return adapter.execute(
            code=code,
            language=language,
            input_payload=tool_input.get("input", {}),
            timeout_seconds=timeout_seconds,
            policy=safety_policy,
        )
    except PlatformControlPlaneError as exc:
        raise CatalogError(exc.code, exc.message, status_code=exc.status_code, details=exc.details or None) from exc


def _serialize_catalog_tool_execution(
    *,
    tool: dict[str, Any],
    input_payload: dict[str, Any],
    request_metadata: dict[str, Any],
    result_payload: dict[str, Any] | None,
    status_code: int,
    started_at: datetime,
    completed_at: datetime,
    duration_ms: int,
) -> dict[str, Any]:
    payload = dict(result_payload) if isinstance(result_payload, dict) else None
    runtime_log = build_catalog_tool_runtime_log(
        tool=tool,
        input_payload=input_payload,
        request_metadata=request_metadata,
        result_payload=payload,
        status_code=status_code,
        duration_ms=duration_ms,
    )
    return {
        "tool": tool,
        "execution": {
            "input": input_payload,
            "request_metadata": request_metadata,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "status_code": status_code,
            "ok": payload is not None and 200 <= status_code < 300 and not payload.get("error"),
            "result": payload,
            "runtime_log": runtime_log,
        },
    }


def _coerce_agent_spec(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    instructions = str(payload.get("instructions", "")).strip()
    if not name:
        raise CatalogError("invalid_name", "name is required")
    if not description:
        raise CatalogError("invalid_description", "description is required")
    tool_refs_raw = payload.get("tool_refs", [])
    if not isinstance(tool_refs_raw, list):
        raise CatalogError("invalid_tool_refs", "tool_refs must be an array")
    tool_refs = [str(item).strip() for item in tool_refs_raw if str(item).strip()]
    mcp_server_refs_raw = payload.get("mcp_server_refs", [])
    if not isinstance(mcp_server_refs_raw, list):
        raise CatalogError("invalid_mcp_server_refs", "mcp_server_refs must be an array")
    mcp_server_refs = [str(item).strip() for item in mcp_server_refs_raw if str(item).strip()]
    agent_domain = str(payload.get("agent_domain") or "default").strip() or "default"
    try:
        agent_type = coerce_user_agent_type(payload.get("agent_type"))
    except ValueError as exc:
        raise CatalogError("invalid_agent_type", str(exc)) from exc
    if agent_type != "workflow" and not instructions:
        raise CatalogError("invalid_instructions", "instructions is required")
    try:
        channel_type = coerce_channel_type(payload.get("channel_type"))
    except ValueError as exc:
        raise CatalogError("invalid_channel_type", str(exc)) from exc
    try:
        interface_type = coerce_interface_type(payload.get("interface_type"))
    except ValueError as exc:
        raise CatalogError("invalid_interface_type", str(exc)) from exc
    runtime_constraints = payload.get("runtime_constraints")
    if not isinstance(runtime_constraints, dict):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints must be an object")
    if not isinstance(runtime_constraints.get("internet_required"), bool):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints.internet_required must be a boolean")
    if not isinstance(runtime_constraints.get("sandbox_required"), bool):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints.sandbox_required must be a boolean")
    try:
        coerced_runtime_prompts = coerce_agent_runtime_prompts(
            payload.get("runtime_prompts"),
            default_when_missing=True,
            agent_type=agent_type,
        )
    except ValueError as exc:
        raise CatalogError("invalid_runtime_prompts", str(exc)) from exc
    try:
        workflow_definition = normalize_workflow_definition(payload.get("workflow_definition"))
    except ValueError as exc:
        raise CatalogError("invalid_workflow_definition", str(exc)) from exc
    default_model_ref_raw = payload.get("default_model_ref")
    default_model_ref = str(default_model_ref_raw).strip() if default_model_ref_raw is not None else None
    if channel_type == CHANNEL_TYPE_VANESSA_WEBAPP and interface_type != INTERFACE_TYPE_CHAT:
        raise CatalogError("invalid_interface_type", "channel_type vanessa_webapp currently requires interface_type chat")
    return {
        "name": name,
        "description": description,
        "instructions": instructions,
        "runtime_prompts": coerced_runtime_prompts,
        "default_model_ref": default_model_ref or None,
        "tool_refs": tool_refs,
        "mcp_server_refs": mcp_server_refs,
        "agent_domain": agent_domain,
        "agent_type": agent_type,
        "channel_type": channel_type,
        "interface_type": interface_type,
        "workflow_definition": workflow_definition,
        "runtime_constraints": {
            "internet_required": bool(runtime_constraints["internet_required"]),
            "sandbox_required": bool(runtime_constraints["sandbox_required"]),
        },
    }


def _coerce_tool_spec(database_url: str, payload: dict[str, Any], *, config: Any | None = None) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    execution_backend = str(payload.get("execution_backend", "")).strip().lower()
    if not name:
        raise CatalogError("invalid_name", "name is required")
    if not description:
        raise CatalogError("invalid_description", "description is required")
    if execution_backend not in _VALID_TOOL_BACKENDS:
        raise CatalogError(
            "invalid_execution_backend",
            "execution_backend must be sandbox_python, web_search, internal_http, knowledge_base_retrieval, image_analysis, or image_generation",
        )
    input_schema = payload.get("input_schema")
    output_schema = payload.get("output_schema")
    safety_policy = payload.get("safety_policy")
    execution_config = payload.get("execution_config")
    permissions = payload.get("permissions")
    if not isinstance(input_schema, dict):
        raise CatalogError("invalid_input_schema", "input_schema must be an object")
    if not isinstance(output_schema, dict):
        raise CatalogError("invalid_output_schema", "output_schema must be an object")
    _validate_json_schema(input_schema, field_name="input_schema")
    _validate_json_schema(output_schema, field_name="output_schema")
    if not isinstance(safety_policy, dict):
        raise CatalogError("invalid_safety_policy", "safety_policy must be an object")
    if not isinstance(execution_config, dict):
        raise CatalogError("invalid_execution_config", "execution_config must be an object")
    if not isinstance(permissions, dict):
        raise CatalogError("invalid_permissions", "permissions must be an object")
    offline_compatible = payload.get("offline_compatible")
    if not isinstance(offline_compatible, bool):
        raise CatalogError("invalid_offline_compatible", "offline_compatible must be a boolean")
    ensure_execution_config(database_url, config=config, execution_backend=execution_backend, execution_config=execution_config)
    return {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "safety_policy": safety_policy,
        "offline_compatible": offline_compatible,
        "execution_backend": execution_backend,
        "execution_config": execution_config,
        "permissions": permissions,
    }


def _coerce_mcp_server_spec(database_url: str, payload: dict[str, Any], *, current_id: str | None) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    slug = str(payload.get("slug", "")).strip().lower()
    description = str(payload.get("description", "")).strip()
    backing_tool_id = str(payload.get("backing_tool_id", "")).strip()
    exposed_tool_name = str(payload.get("exposed_tool_name", "")).strip()
    enabled = payload.get("enabled")
    if not name:
        raise CatalogError("invalid_name", "name is required")
    if not slug or not _SLUG_PATTERN.match(slug):
        raise CatalogError("invalid_slug", "slug must start with a lowercase letter or number and contain only letters, numbers, dots, dashes, or underscores")
    if not description:
        raise CatalogError("invalid_description", "description is required")
    if not exposed_tool_name or not _SLUG_PATTERN.match(exposed_tool_name.lower()):
        raise CatalogError("invalid_exposed_tool_name", "exposed_tool_name is required")
    if not isinstance(enabled, bool):
        raise CatalogError("invalid_enabled", "enabled must be a boolean")
    _ensure_unique_mcp_slug(database_url, slug=slug, current_id=current_id)
    _ensure_tool_eligible_for_mcp(database_url, tool_id=backing_tool_id)

    input_schema = payload.get("input_schema")
    output_schema = payload.get("output_schema")
    if not isinstance(input_schema, dict):
        raise CatalogError("invalid_input_schema", "input_schema must be an object")
    if not isinstance(output_schema, dict):
        raise CatalogError("invalid_output_schema", "output_schema must be an object")
    _validate_json_schema(input_schema, field_name="input_schema")
    _validate_json_schema(output_schema, field_name="output_schema")

    return {
        "name": name,
        "slug": slug,
        "description": description,
        "backing_tool_id": backing_tool_id,
        "exposed_tool_name": exposed_tool_name,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "metadata": _coerce_mcp_metadata(payload.get("metadata"), require_all=True),
        "authorization_policy": _coerce_authorization_policy(payload.get("authorization_policy")),
        "enabled": enabled,
    }


def _coerce_mcp_metadata(value: Any, *, require_all: bool) -> dict[str, Any]:
    if value is None and not require_all:
        raw: dict[str, Any] = {}
    elif isinstance(value, dict):
        raw = value
    else:
        raise CatalogError("invalid_mcp_metadata", "metadata must be an object")

    defaults: dict[str, Any] = {
        "category": "custom",
        "capabilities": [],
        "local": False,
        "stateless": True,
        "sandboxed": False,
        "risk_level": "medium",
        "data_access": "none",
        "output_freshness": "runtime_generated",
        "audit_level": "standard",
    }
    required_fields = set(defaults)
    if require_all:
        missing = sorted(field for field in required_fields if field not in raw)
        if missing:
            raise CatalogError("invalid_mcp_metadata", f"metadata is missing required fields: {', '.join(missing)}")

    category = _coerce_enum_metadata(raw.get("category", defaults["category"]), _VALID_MCP_METADATA_CATEGORIES, field_name="category")
    risk_level = _coerce_enum_metadata(raw.get("risk_level", defaults["risk_level"]), _VALID_MCP_METADATA_RISK_LEVELS, field_name="risk_level")
    data_access = _coerce_enum_metadata(raw.get("data_access", defaults["data_access"]), _VALID_MCP_METADATA_DATA_ACCESS, field_name="data_access")
    output_freshness = _coerce_enum_metadata(
        raw.get("output_freshness", defaults["output_freshness"]),
        _VALID_MCP_METADATA_OUTPUT_FRESHNESS,
        field_name="output_freshness",
    )
    audit_level = _coerce_enum_metadata(raw.get("audit_level", defaults["audit_level"]), _VALID_MCP_METADATA_AUDIT_LEVELS, field_name="audit_level")
    capabilities = raw.get("capabilities", defaults["capabilities"])
    if not isinstance(capabilities, list):
        raise CatalogError("invalid_mcp_metadata", "metadata.capabilities must be an array")
    normalized_capabilities: list[str] = []
    seen_capabilities: set[str] = set()
    for item in capabilities:
        tag = str(item).strip().lower().replace("_", "-")
        tag = re.sub(r"[^a-z0-9-]+", "-", tag)
        tag = re.sub(r"-+", "-", tag).strip("-")
        if not tag:
            continue
        if not _TAG_PATTERN.match(tag):
            raise CatalogError("invalid_mcp_metadata", "metadata.capabilities entries must be lowercase slug tags")
        if tag not in seen_capabilities:
            normalized_capabilities.append(tag)
            seen_capabilities.add(tag)

    return {
        "category": category,
        "capabilities": normalized_capabilities,
        "local": _coerce_boolean_metadata(raw.get("local", defaults["local"]), field_name="local"),
        "stateless": _coerce_boolean_metadata(raw.get("stateless", defaults["stateless"]), field_name="stateless"),
        "sandboxed": _coerce_boolean_metadata(raw.get("sandboxed", defaults["sandboxed"]), field_name="sandboxed"),
        "risk_level": risk_level,
        "data_access": data_access,
        "output_freshness": output_freshness,
        "audit_level": audit_level,
    }


def _coerce_enum_metadata(value: Any, allowed_values: set[str], *, field_name: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in allowed_values:
        raise CatalogError("invalid_mcp_metadata", f"metadata.{field_name} must be one of {', '.join(sorted(allowed_values))}")
    return normalized


def _coerce_boolean_metadata(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise CatalogError("invalid_mcp_metadata", f"metadata.{field_name} must be a boolean")
    return value


def _coerce_authorization_policy(value: Any) -> dict[str, list[str]]:
    raw = value if isinstance(value, dict) else {}
    fields = ["agent_ids", "agent_domains", "agent_roles", "user_roles", "user_ids", "user_group_ids"]
    policy: dict[str, list[str]] = {}
    for field in fields:
        items = raw.get(field, ["*"])
        if not isinstance(items, list):
            raise CatalogError("invalid_authorization_policy", f"authorization_policy.{field} must be an array")
        normalized = [str(item).strip() for item in items if str(item).strip()]
        policy[field] = normalized or ["*"]
    return policy


def _validate_json_schema(schema: dict[str, Any], *, field_name: str) -> None:
    if Draft202012Validator is None:
        if not isinstance(schema, dict):
            raise CatalogError(f"invalid_{field_name}", f"{field_name} must be a valid JSON Schema")
        schema_type = schema.get("type")
        if schema_type is not None and schema_type not in {"object", "array", "string", "integer", "number", "boolean", "null"}:
            raise CatalogError(f"invalid_{field_name}", f"{field_name} must be a valid JSON Schema")
        return
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise CatalogError(f"invalid_{field_name}", f"{field_name} must be a valid JSON Schema", details={"schema_error": str(exc)}) from exc


def _validate_json_payload(schema: dict[str, Any], payload: dict[str, Any], *, field_name: str) -> list[str]:
    if Draft202012Validator is None:
        errors: list[str] = []
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        for key in required:
            if isinstance(key, str) and key not in payload:
                errors.append(f"{field_name}: '{key}' is required")
        additional_properties = schema.get("additionalProperties")
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if additional_properties is False:
            for key in payload:
                if key not in properties:
                    errors.append(f"{field_name}: Additional properties are not allowed ('{key}' was unexpected)")
        return errors
    try:
        validator = Draft202012Validator(schema)
        return [f"{field_name}: {error.message}" for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path))]
    except SchemaError as exc:
        return [f"{field_name}: invalid schema: {exc}"]


def _ensure_unique_mcp_slug(database_url: str, *, slug: str, current_id: str | None) -> None:
    existing = _find_mcp_server_by_slug(database_url, slug)
    if existing is not None and str(existing.get("id")) != str(current_id or ""):
        raise CatalogError("duplicate_mcp_slug", "MCP server slug already exists", status_code=409)


def _ensure_tool_eligible_for_mcp(database_url: str, *, tool_id: str) -> dict[str, Any]:
    if not tool_id:
        raise CatalogError("invalid_backing_tool_id", "backing_tool_id is required")
    tool = get_catalog_tool(database_url, tool_id=tool_id)
    status = tool.get("validation_status") if isinstance(tool.get("validation_status"), dict) else {}
    if not tool.get("published"):
        raise CatalogError("backing_tool_not_published", "Only published tools can back MCP servers")
    if status.get("last_validation_status") != "success" or not status.get("is_validation_current"):
        raise CatalogError("backing_tool_not_validated", "Only currently validated tools can back MCP servers")
    return tool


def _metadata_string(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    normalized = str(value).strip() if value is not None else ""
    return normalized or None


def _tool_execution_backend(spec: dict[str, Any]) -> str:
    return tool_execution_backend(spec)


def _metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    if value in {None, ""}:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _policy_list(policy: dict[str, Any], field: str) -> set[str]:
    items = policy.get(field)
    if not isinstance(items, list):
        return {"*"}
    normalized = {str(item).strip().lower() for item in items if str(item).strip()}
    return normalized or {"*"}


def _policy_allows_value(allowed: set[str], value: str | None) -> bool:
    return "*" in allowed or (value is not None and str(value).strip().lower() in allowed)


def _mcp_policy_allows(
    policy: dict[str, Any],
    *,
    agent_id: str | None,
    agent_domain: str | None,
    delegated_user_id: int | None,
    delegated_user_role: str | None,
    user_group_ids: set[str],
) -> bool:
    if not _policy_allows_value(_policy_list(policy, "agent_ids"), agent_id):
        return False
    if not _policy_allows_value(_policy_list(policy, "agent_domains"), agent_domain or "default"):
        return False
    if not _policy_allows_value(_policy_list(policy, "user_roles"), delegated_user_role):
        return False
    allowed_user_ids = _policy_list(policy, "user_ids")
    if "*" not in allowed_user_ids and (delegated_user_id is None or str(delegated_user_id) not in allowed_user_ids):
        return False
    allowed_group_ids = _policy_list(policy, "user_group_ids")
    if "*" not in allowed_group_ids and not ({item.lower() for item in user_group_ids} & allowed_group_ids):
        return False
    return True


def _entity_status(publish: bool) -> str:
    return "published" if publish else "draft"


def _coerce_visibility(raw_value: Any) -> str:
    visibility = str(raw_value or "private").strip().lower() or "private"
    if visibility not in _VALID_VISIBILITIES:
        raise CatalogError("invalid_visibility", "visibility must be private, unlisted, or public")
    return visibility


def _coerce_publish(payload: dict[str, Any]) -> bool:
    publish = payload.get("publish")
    if not isinstance(publish, bool):
        raise CatalogError("invalid_publish", "publish must be a boolean")
    return publish


def _next_version(current_version: Any) -> str:
    normalized = str(current_version or "").strip()
    match = _VERSION_PATTERN.match(normalized)
    if not match:
        return "v2"
    return f"v{int(match.group('number')) + 1}"
