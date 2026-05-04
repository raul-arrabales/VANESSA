from __future__ import annotations

from typing import Any

from ..repositories.registry import (
    create_registry_entity,
    create_registry_version,
    find_registry_entity,
    list_registry_entities,
    list_registry_versions,
)
from .agent_prompt_defaults import coerce_agent_runtime_prompts

_ENTITY_TYPES = {"model", "agent", "tool"}


def _normalize_entity_type(entity_type: str) -> str:
    normalized = entity_type.strip().lower()
    if normalized.endswith("s"):
        normalized = normalized[:-1]
    if normalized not in _ENTITY_TYPES:
        raise ValueError("invalid_entity_type")
    return normalized


def _initial_status_for_type(entity_type: str) -> str:
    if entity_type == "model":
        return "available"
    return "draft"


def _validate_spec(entity_type: str, spec: dict[str, Any]) -> None:
    if entity_type == "agent":
        required = [
            "name",
            "description",
            "instructions",
            "runtime_prompts",
            "default_model_ref",
            "tool_refs",
            "runtime_constraints",
        ]
        for key in required:
            if key not in spec:
                raise ValueError(f"missing_agent_field:{key}")
        try:
            coerce_agent_runtime_prompts(spec.get("runtime_prompts"), default_when_missing=False)
        except ValueError as exc:
            raise ValueError(f"invalid_agent_field:{exc}") from exc
    elif entity_type == "tool":
        required = [
            "name",
            "description",
            "transport",
            "connection_profile_ref",
            "tool_name",
            "input_schema",
            "output_schema",
            "safety_policy",
            "offline_compatible",
        ]
        for key in required:
            if key not in spec:
                raise ValueError(f"missing_tool_field:{key}")
        transport = str(spec.get("transport", "")).strip().lower()
        if transport not in {"mcp", "sandbox_http"}:
            raise ValueError("invalid_transport")
        if str(spec.get("connection_profile_ref", "")).strip().lower() != "default":
            raise ValueError("invalid_connection_profile_ref")


def create_entity_with_version(
    database_url: str,
    *,
    entity_type: str,
    entity_id: str,
    owner_user_id: int,
    visibility: str,
    spec: dict[str, Any],
    version: str,
    publish: bool,
) -> dict[str, Any]:
    normalized_type = _normalize_entity_type(entity_type)
    _validate_spec(normalized_type, spec)

    entity = create_registry_entity(
        database_url,
        entity_id=entity_id,
        entity_type=normalized_type,
        owner_user_id=owner_user_id,
        visibility=visibility,
        status=_initial_status_for_type(normalized_type),
    )
    created_version = create_registry_version(
        database_url,
        entity_id=entity_id,
        version=version,
        spec_json=spec,
        set_current=True,
        published=publish,
    )

    return {
        "entity": entity,
        "version": created_version,
    }


def create_entity_version(
    database_url: str,
    *,
    entity_type: str,
    entity_id: str,
    version: str,
    spec: dict[str, Any],
    publish: bool,
) -> dict[str, Any]:
    normalized_type = _normalize_entity_type(entity_type)
    _validate_spec(normalized_type, spec)

    entity = find_registry_entity(database_url, entity_type=normalized_type, entity_id=entity_id)
    if entity is None:
        raise LookupError("entity_not_found")

    created_version = create_registry_version(
        database_url,
        entity_id=entity_id,
        version=version,
        spec_json=spec,
        set_current=True,
        published=publish,
    )

    return {
        "entity": entity,
        "version": created_version,
    }


def get_entity(database_url: str, *, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    normalized_type = _normalize_entity_type(entity_type)
    return find_registry_entity(database_url, entity_type=normalized_type, entity_id=entity_id)


def list_entities(database_url: str, *, entity_type: str) -> list[dict[str, Any]]:
    normalized_type = _normalize_entity_type(entity_type)
    return list_registry_entities(database_url, entity_type=normalized_type)


def get_entity_versions(database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
    return list_registry_versions(database_url, entity_id=entity_id)
