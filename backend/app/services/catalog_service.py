from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from ..repositories.model_access import find_model_definition
from ..repositories.registry import (
    create_registry_entity,
    create_registry_version,
    delete_registry_entity,
    find_registry_entity,
    list_registry_entities,
    update_registry_entity,
)
from .agent_prompt_defaults import default_agent_runtime_prompts, normalize_agent_runtime_prompts
from .knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID
from .platform_service import resolve_mcp_runtime_adapter, resolve_sandbox_execution_adapter
from .platform_types import PlatformControlPlaneError

_ENTITY_TYPE_AGENT = "agent"
_ENTITY_TYPE_TOOL = "tool"
_VALID_VISIBILITIES = {"private", "unlisted", "public"}
_VALID_TOOL_TRANSPORTS = {"mcp", "sandbox_http"}
_VERSION_PATTERN = re.compile(r"^v(?P<number>\d+)$", re.IGNORECASE)
_PLATFORM_AGENT_IDS = {KNOWLEDGE_CHAT_AGENT_ID}


@dataclass(slots=True)
class CatalogError(RuntimeError):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None


def list_catalog_agents(database_url: str) -> list[dict[str, Any]]:
    return [_serialize_catalog_row(row, entity_type=_ENTITY_TYPE_AGENT) for row in list_registry_entities(database_url, entity_type=_ENTITY_TYPE_AGENT)]


def list_catalog_tools(database_url: str) -> list[dict[str, Any]]:
    return [_serialize_catalog_row(row, entity_type=_ENTITY_TYPE_TOOL) for row in list_registry_entities(database_url, entity_type=_ENTITY_TYPE_TOOL)]


def get_catalog_agent(database_url: str, *, agent_id: str) -> dict[str, Any]:
    row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_AGENT, entity_id=agent_id)
    if row is None:
        raise CatalogError("agent_not_found", "Agent not found", status_code=404)
    return _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_AGENT)


def get_catalog_tool(database_url: str, *, tool_id: str) -> dict[str, Any]:
    row = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=tool_id)
    if row is None:
        raise CatalogError("tool_not_found", "Tool not found", status_code=404)
    return _serialize_catalog_row(row, entity_type=_ENTITY_TYPE_TOOL)


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
) -> dict[str, Any]:
    entity_id = str(payload.get("id", "")).strip()
    if not entity_id:
        raise CatalogError("invalid_tool_id", "id is required")
    if find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=entity_id) is not None:
        raise CatalogError("duplicate_tool", "Tool already exists", status_code=409)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", "private"))
    spec = _coerce_tool_spec(payload)
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
) -> dict[str, Any]:
    existing = find_registry_entity(database_url, entity_type=_ENTITY_TYPE_TOOL, entity_id=tool_id)
    if existing is None:
        raise CatalogError("tool_not_found", "Tool not found", status_code=404)

    publish = _coerce_publish(payload)
    visibility = _coerce_visibility(payload.get("visibility", existing.get("visibility", "private")))
    spec = _coerce_tool_spec(payload)
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


def validate_catalog_tool(
    database_url: str,
    *,
    config: Any,
    tool_id: str,
) -> dict[str, Any]:
    tool = get_catalog_tool(database_url, tool_id=tool_id)
    spec = dict(tool["spec"])
    transport = str(spec.get("transport", "")).strip().lower()
    runtime_checks, errors = _validate_catalog_tool_transport(
        database_url=database_url,
        config=config,
        transport=transport,
        spec=spec,
    )
    warnings: list[str] = []

    return {
        "tool": tool,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
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

    transport = str(spec.get("transport", "")).strip().lower()
    request_metadata = payload.get("request_metadata") if isinstance(payload.get("request_metadata"), dict) else {}
    if actor_user_id is not None and "actor_user_id" not in request_metadata:
        request_metadata = {**request_metadata, "actor_user_id": actor_user_id}

    result_payload, status_code = _execute_catalog_tool_transport(
        database_url=database_url,
        config=config,
        transport=transport,
        spec=spec,
        tool_input=tool_input,
        request_metadata=request_metadata,
    )
    return _serialize_catalog_tool_execution(
        tool=tool,
        input_payload=tool_input,
        request_metadata=request_metadata,
        result_payload=result_payload,
        status_code=status_code,
    )


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
        tool = _serialize_catalog_row(tool_row, entity_type=_ENTITY_TYPE_TOOL)
        tool_spec = dict(tool["spec"])
        transport = str(tool_spec.get("transport", "")).strip().lower()
        offline_compatible = bool(tool_spec.get("offline_compatible", False))
        resolved_tools.append(
            {
                "id": tool["id"],
                "name": tool_spec.get("name"),
                "transport": transport,
                "offline_compatible": offline_compatible,
            }
        )
        if transport == "sandbox_http":
            derived_runtime_requirements["sandbox_required"] = True
        if not offline_compatible:
            derived_runtime_requirements["internet_required"] = True

    runtime_constraints = spec.get("runtime_constraints") if isinstance(spec.get("runtime_constraints"), dict) else {}
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
            "derived_runtime_requirements": derived_runtime_requirements,
        },
    }


def _serialize_catalog_row(row: dict[str, Any], *, entity_type: Literal["agent", "tool"]) -> dict[str, Any]:
    current_spec = row.get("current_spec") if isinstance(row.get("current_spec"), dict) else {}
    if entity_type == _ENTITY_TYPE_AGENT:
        current_spec = _normalize_agent_spec_for_response(current_spec)
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
        "spec": current_spec,
    }
    if entity_type == _ENTITY_TYPE_AGENT:
        serialized["agent_kind"] = "platform" if _is_platform_agent(str(row.get("entity_id", ""))) else "user"
        serialized["is_platform_agent"] = serialized["agent_kind"] == "platform"
    return serialized


def _is_platform_agent(agent_id: str) -> bool:
    return str(agent_id).strip() in _PLATFORM_AGENT_IDS


def _normalize_agent_spec_for_response(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(spec)
    normalized["runtime_prompts"] = normalize_agent_runtime_prompts(normalized.get("runtime_prompts"))
    return normalized


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
) -> dict[str, Any]:
    payload = dict(result_payload) if isinstance(result_payload, dict) else None
    return {
        "tool": tool,
        "execution": {
            "input": input_payload,
            "request_metadata": request_metadata,
            "status_code": status_code,
            "ok": payload is not None and 200 <= status_code < 300 and not payload.get("error"),
            "result": payload,
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
    if not instructions:
        raise CatalogError("invalid_instructions", "instructions is required")
    tool_refs_raw = payload.get("tool_refs", [])
    if not isinstance(tool_refs_raw, list):
        raise CatalogError("invalid_tool_refs", "tool_refs must be an array")
    tool_refs = [str(item).strip() for item in tool_refs_raw if str(item).strip()]
    runtime_constraints = payload.get("runtime_constraints")
    if not isinstance(runtime_constraints, dict):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints must be an object")
    if not isinstance(runtime_constraints.get("internet_required"), bool):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints.internet_required must be a boolean")
    if not isinstance(runtime_constraints.get("sandbox_required"), bool):
        raise CatalogError("invalid_runtime_constraints", "runtime_constraints.sandbox_required must be a boolean")
    runtime_prompts = payload.get("runtime_prompts")
    if runtime_prompts is None:
        coerced_runtime_prompts = default_agent_runtime_prompts()
    elif not isinstance(runtime_prompts, dict):
        raise CatalogError("invalid_runtime_prompts", "runtime_prompts must be an object")
    else:
        retrieval_context = str(runtime_prompts.get("retrieval_context", "")).strip()
        if not retrieval_context:
            raise CatalogError("invalid_runtime_prompts", "runtime_prompts.retrieval_context is required")
        coerced_runtime_prompts = {"retrieval_context": retrieval_context}
    default_model_ref_raw = payload.get("default_model_ref")
    default_model_ref = str(default_model_ref_raw).strip() if default_model_ref_raw is not None else None
    return {
        "name": name,
        "description": description,
        "instructions": instructions,
        "runtime_prompts": coerced_runtime_prompts,
        "default_model_ref": default_model_ref or None,
        "tool_refs": tool_refs,
        "runtime_constraints": {
            "internet_required": bool(runtime_constraints["internet_required"]),
            "sandbox_required": bool(runtime_constraints["sandbox_required"]),
        },
    }


def _coerce_tool_spec(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    tool_name = str(payload.get("tool_name", "")).strip()
    transport = str(payload.get("transport", "")).strip().lower()
    connection_profile_ref = str(payload.get("connection_profile_ref", "")).strip().lower()
    if not name:
        raise CatalogError("invalid_name", "name is required")
    if not description:
        raise CatalogError("invalid_description", "description is required")
    if transport not in _VALID_TOOL_TRANSPORTS:
        raise CatalogError("invalid_transport", "transport must be mcp or sandbox_http")
    if connection_profile_ref != "default":
        raise CatalogError("invalid_connection_profile_ref", "connection_profile_ref must be 'default'")
    if not tool_name:
        raise CatalogError("invalid_tool_name", "tool_name is required")
    input_schema = payload.get("input_schema")
    output_schema = payload.get("output_schema")
    safety_policy = payload.get("safety_policy")
    if not isinstance(input_schema, dict):
        raise CatalogError("invalid_input_schema", "input_schema must be an object")
    if not isinstance(output_schema, dict):
        raise CatalogError("invalid_output_schema", "output_schema must be an object")
    if not isinstance(safety_policy, dict):
        raise CatalogError("invalid_safety_policy", "safety_policy must be an object")
    offline_compatible = payload.get("offline_compatible")
    if not isinstance(offline_compatible, bool):
        raise CatalogError("invalid_offline_compatible", "offline_compatible must be a boolean")
    return {
        "name": name,
        "description": description,
        "transport": transport,
        "connection_profile_ref": connection_profile_ref,
        "tool_name": tool_name,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "safety_policy": safety_policy,
        "offline_compatible": offline_compatible,
    }


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
