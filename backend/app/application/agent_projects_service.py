from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..repositories.agent_projects import (
    create_agent_project as create_project_row,
    get_agent_project,
    list_agent_projects as list_project_rows,
    set_published_agent_id,
    update_agent_project as update_project_row,
)
from ..repositories.model_access import find_model_definition
from ..repositories.registry import find_registry_entity
from ..services.agent_prompt_defaults import coerce_agent_runtime_prompts, normalize_agent_runtime_prompts
from .catalog_management_service import create_catalog_agent, update_catalog_agent

_VALID_VISIBILITIES = {"private", "unlisted", "public"}


class AgentProjectError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def list_agent_projects(database_url: str, *, actor_user_id: int, actor_role: str) -> list[dict[str, Any]]:
    rows = list_project_rows(database_url, owner_user_id=None if actor_role == "superadmin" else actor_user_id)
    return [_serialize_project(row) for row in rows]


def get_agent_project_detail(
    database_url: str,
    *,
    project_id: str,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    row = _require_project(database_url, project_id=project_id, actor_user_id=actor_user_id, actor_role=actor_role)
    return _serialize_project(row)


def create_agent_project(
    database_url: str,
    *,
    payload: dict[str, Any],
    owner_user_id: int,
) -> dict[str, Any]:
    project_id = str(payload.get("id", "")).strip()
    if not project_id:
        raise AgentProjectError("invalid_project_id", "id is required")
    if get_agent_project(database_url, project_id=project_id) is not None:
        raise AgentProjectError("duplicate_project", "Agent project already exists", status_code=409)
    spec = _coerce_project_spec(payload)
    row = create_project_row(
        database_url,
        project_id=project_id,
        owner_user_id=owner_user_id,
        spec=spec,
        visibility=_coerce_visibility(payload.get("visibility", "private")),
    )
    return _serialize_project(row)


def update_agent_project(
    database_url: str,
    *,
    project_id: str,
    payload: dict[str, Any],
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    existing = _require_project(database_url, project_id=project_id, actor_user_id=actor_user_id, actor_role=actor_role)
    row = update_project_row(
        database_url,
        project_id=project_id,
        spec=_coerce_project_spec(payload),
        visibility=_coerce_visibility(payload.get("visibility", existing.get("visibility", "private"))),
        updated_by_user_id=actor_user_id,
    )
    if row is None:
        raise AgentProjectError("project_not_found", "Agent project not found", status_code=404)
    return _serialize_project(row)


def validate_agent_project(
    database_url: str,
    *,
    project_id: str,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    project = get_agent_project_detail(
        database_url,
        project_id=project_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    spec = dict(project["spec"])
    errors: list[str] = []
    warnings: list[str] = []

    default_model_ref = spec.get("default_model_ref")
    if default_model_ref and find_model_definition(database_url, str(default_model_ref)) is None:
        errors.append(f"Model '{default_model_ref}' does not exist.")

    derived_runtime_requirements = {"internet_required": False, "sandbox_required": False}
    resolved_tools: list[dict[str, Any]] = []
    for tool_ref in spec.get("tool_refs", []):
        tool_row = find_registry_entity(database_url, entity_type="tool", entity_id=str(tool_ref))
        if tool_row is None:
            errors.append(f"Tool '{tool_ref}' does not exist.")
            continue
        tool_spec = tool_row.get("current_spec") if isinstance(tool_row.get("current_spec"), dict) else {}
        transport = str(tool_spec.get("transport", "")).strip().lower()
        offline_compatible = bool(tool_spec.get("offline_compatible", False))
        resolved_tools.append(
            {
                "id": str(tool_row.get("entity_id", "")),
                "name": str(tool_spec.get("name", "")),
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
        errors.append("Project references sandbox tools but runtime_constraints.sandbox_required is false.")
    if derived_runtime_requirements["internet_required"] and not bool(runtime_constraints.get("internet_required", False)):
        errors.append("Project references online-only tools but runtime_constraints.internet_required is false.")

    return {
        "agent_project": project,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "resolved_tools": resolved_tools,
            "derived_runtime_requirements": derived_runtime_requirements,
        },
    }


def publish_agent_project(
    database_url: str,
    *,
    project_id: str,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    project = get_agent_project_detail(
        database_url,
        project_id=project_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    payload = _compile_catalog_payload(project)
    published_agent_id = str(project.get("published_agent_id") or f"agent.project.{project_id}")
    existing = find_registry_entity(database_url, entity_type="agent", entity_id=published_agent_id)
    if existing is None:
        published_agent = create_catalog_agent(
            database_url,
            payload={"id": published_agent_id, **payload},
            owner_user_id=actor_user_id,
        )
    else:
        published_agent = update_catalog_agent(
            database_url,
            agent_id=published_agent_id,
            payload=payload,
        )
    updated = set_published_agent_id(
        database_url,
        project_id=project_id,
        published_agent_id=published_agent_id,
    )
    if updated is None:
        raise AgentProjectError("project_not_found", "Agent project not found", status_code=404)
    return {
        "agent_project": _serialize_project(updated),
        "publish_result": {
            "agent_id": published_agent_id,
            "catalog_agent": published_agent,
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def build_agent_project_preview(
    database_url: str,
    *,
    project_id: str,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    project = get_agent_project_detail(
        database_url,
        project_id=project_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    spec = dict(project["spec"])
    return {
        "project_id": project["id"],
        "assistant_ref": str(project.get("published_agent_id") or f"agent.project.{project['id']}"),
        "playground_kind": "chat",
        "default_model_ref": spec.get("default_model_ref"),
        "tool_refs": list(spec.get("tool_refs", [])),
        "runtime_constraints": dict(spec.get("runtime_constraints") or {}),
        "workflow_definition": dict(spec.get("workflow_definition") or {}),
    }


def _require_project(
    database_url: str,
    *,
    project_id: str,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    row = get_agent_project(database_url, project_id=project_id)
    if row is None:
        raise AgentProjectError("project_not_found", "Agent project not found", status_code=404)
    if actor_role != "superadmin" and int(row.get("owner_user_id") or 0) != actor_user_id:
        raise AgentProjectError("project_not_found", "Agent project not found", status_code=404)
    return row


def _serialize_project(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "owner_user_id": row.get("owner_user_id"),
        "published_agent_id": row.get("published_agent_id"),
        "current_version": int(row.get("current_version", 1) or 1),
        "visibility": str(row.get("visibility", "private")),
        "created_at": _serialize_datetime(row.get("created_at")),
        "updated_at": _serialize_datetime(row.get("updated_at")),
        "spec": {
            "name": str(row.get("name", "")),
            "description": str(row.get("description", "")),
            "instructions": str(row.get("instructions", "")),
            "runtime_prompts": normalize_agent_runtime_prompts(row.get("runtime_prompts")),
            "default_model_ref": _string_or_none(row.get("default_model_ref")),
            "tool_refs": list(row.get("tool_refs") or []),
            "workflow_definition": dict(row.get("workflow_definition") or {}),
            "tool_policy": dict(row.get("tool_policy") or {}),
            "runtime_constraints": dict(row.get("runtime_constraints") or {}),
        },
    }


def _coerce_project_spec(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    instructions = str(payload.get("instructions", "")).strip()
    if not name:
        raise AgentProjectError("invalid_name", "name is required")
    if not description:
        raise AgentProjectError("invalid_description", "description is required")
    if not instructions:
        raise AgentProjectError("invalid_instructions", "instructions is required")
    try:
        coerced_runtime_prompts = coerce_agent_runtime_prompts(
            payload.get("runtime_prompts"),
            default_when_missing=True,
        )
    except ValueError as exc:
        raise AgentProjectError("invalid_runtime_prompts", str(exc)) from exc
    tool_refs_raw = payload.get("tool_refs", [])
    if not isinstance(tool_refs_raw, list):
        raise AgentProjectError("invalid_tool_refs", "tool_refs must be an array")
    runtime_constraints = payload.get("runtime_constraints")
    if not isinstance(runtime_constraints, dict):
        raise AgentProjectError("invalid_runtime_constraints", "runtime_constraints must be an object")
    if not isinstance(runtime_constraints.get("internet_required"), bool):
        raise AgentProjectError("invalid_runtime_constraints", "runtime_constraints.internet_required must be a boolean")
    if not isinstance(runtime_constraints.get("sandbox_required"), bool):
        raise AgentProjectError("invalid_runtime_constraints", "runtime_constraints.sandbox_required must be a boolean")
    workflow_definition = payload.get("workflow_definition", {})
    tool_policy = payload.get("tool_policy", {})
    if not isinstance(workflow_definition, dict):
        raise AgentProjectError("invalid_workflow_definition", "workflow_definition must be an object")
    if not isinstance(tool_policy, dict):
        raise AgentProjectError("invalid_tool_policy", "tool_policy must be an object")
    default_model_ref_raw = payload.get("default_model_ref")
    default_model_ref = str(default_model_ref_raw).strip() if default_model_ref_raw is not None else None
    return {
        "name": name,
        "description": description,
        "instructions": instructions,
        "runtime_prompts": coerced_runtime_prompts,
        "default_model_ref": default_model_ref or None,
        "tool_refs": [str(item).strip() for item in tool_refs_raw if str(item).strip()],
        "workflow_definition": workflow_definition,
        "tool_policy": tool_policy,
        "runtime_constraints": {
            "internet_required": bool(runtime_constraints["internet_required"]),
            "sandbox_required": bool(runtime_constraints["sandbox_required"]),
        },
    }


def _coerce_visibility(raw_value: Any) -> str:
    visibility = str(raw_value or "private").strip().lower() or "private"
    if visibility not in _VALID_VISIBILITIES:
        raise AgentProjectError("invalid_visibility", "visibility must be private, unlisted, or public")
    return visibility


def _compile_catalog_payload(project: dict[str, Any]) -> dict[str, Any]:
    spec = dict(project["spec"])
    return {
        "name": spec["name"],
        "description": spec["description"],
        "instructions": spec["instructions"],
        "runtime_prompts": normalize_agent_runtime_prompts(spec.get("runtime_prompts")),
        "default_model_ref": spec.get("default_model_ref"),
        "tool_refs": list(spec.get("tool_refs", [])),
        "runtime_constraints": dict(spec.get("runtime_constraints") or {}),
        "visibility": str(project.get("visibility", "private")),
        "publish": True,
    }


def _serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value is not None else None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
