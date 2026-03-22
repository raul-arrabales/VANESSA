from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import get_active_credential_secret
from ..repositories.platform_control_plane import count_deployment_bindings_for_served_model
from .modelops_common import ModelOpsError
from .modelops_policy import can_manage_model, get_accessible_model
from .modelops_serializers import serialize_model
from .runtime_profile_service import resolve_runtime_profile


def create_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    provider = str(payload.get("provider", "openai_compatible")).strip().lower()
    backend_kind = str(payload.get("backend", "external_api")).strip().lower()
    owner_type = str(payload.get("owner_type", "")).strip().lower() or modelops_repo.OWNER_USER
    if owner_type not in {modelops_repo.OWNER_PLATFORM, modelops_repo.OWNER_USER}:
        raise ModelOpsError("missing_config", "owner_type must be platform or user", status_code=400)
    if owner_type == modelops_repo.OWNER_PLATFORM and actor_role != "superadmin":
        raise ModelOpsError("forbidden", "Only superadmin can create platform-owned models", status_code=403)
    if backend_kind == "local" and actor_role != "superadmin":
        raise ModelOpsError("forbidden", "Only superadmin can create local platform models", status_code=403)
    if backend_kind == "local" and owner_type != modelops_repo.OWNER_PLATFORM:
        raise ModelOpsError("forbidden", "Local models must be platform-owned", status_code=403)

    requested_task_key = str(payload.get("task_key", "")).strip().lower() or None
    requested_category = str(payload.get("category", "")).strip().lower() or None
    if not requested_task_key:
        raise ModelOpsError("missing_config", "task_key is required", status_code=400)
    if requested_category and requested_category not in {"predictive", "generative"}:
        raise ModelOpsError("missing_config", "category must be predictive or generative", status_code=400)

    inferred_category = requested_category or modelops_repo.infer_category(requested_task_key)
    model_id = str(payload.get("id", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not model_id or not name:
        raise ModelOpsError("missing_config", "id and name are required", status_code=400)

    source_kind = str(payload.get("source", "external_provider" if backend_kind == "external_api" else "local_folder")).strip().lower()
    availability = str(payload.get("availability", "online_only" if backend_kind == "external_api" else "offline_ready")).strip().lower()
    visibility_scope = str(payload.get("visibility_scope", "")).strip().lower() or (
        "private" if owner_type == modelops_repo.OWNER_USER else "platform"
    )
    if visibility_scope not in {"private", "user", "group", "platform"}:
        raise ModelOpsError("missing_config", "visibility_scope must be private, user, group, or platform", status_code=400)
    if owner_type == modelops_repo.OWNER_USER and actor_role == "user" and visibility_scope != "private":
        raise ModelOpsError("forbidden", "Regular users can only create private personal models", status_code=403)
    provider_model_id = str(payload.get("provider_model_id", "")).strip() or None
    credential_id = str(payload.get("credential_id", "")).strip() or None
    owner_user_id = actor_user_id if owner_type == modelops_repo.OWNER_USER else None

    if backend_kind == "external_api":
        if not provider_model_id:
            raise ModelOpsError("missing_config", "provider_model_id is required for cloud models", status_code=400)
        if owner_type == modelops_repo.OWNER_USER and not credential_id:
            raise ModelOpsError("missing_config", "credential_id is required for personal cloud models", status_code=400)
        if credential_id:
            secret = get_active_credential_secret(
                database_url,
                credential_id=credential_id,
                requester_user_id=actor_user_id,
                requester_role=actor_role,
                encryption_key=config.model_credentials_encryption_key,
            )
            if secret is None:
                raise ModelOpsError("missing_config", "Active credential not found", status_code=400)

    created = modelops_repo.upsert_model_record(
        database_url,
        model_id=model_id,
        node_id=config.modelops_node_id,
        name=name,
        provider=provider,
        task_key=requested_task_key,
        category=inferred_category,
        backend_kind=backend_kind,
        source_kind=source_kind,
        availability=availability,
        visibility_scope=visibility_scope,
        owner_type=owner_type,
        owner_user_id=owner_user_id,
        provider_model_id=provider_model_id,
        credential_id=credential_id,
        source_id=str(payload.get("source_id", "")).strip() or None,
        local_path=str(payload.get("local_path", "")).strip() or None,
        status="available",
        lifecycle_state=modelops_repo.LIFECYCLE_REGISTERED,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        comment=str(payload.get("comment", "")).strip() or None,
        model_size_billion=float(payload.get("model_size_billion")) if payload.get("model_size_billion") is not None else None,
        created_by_user_id=actor_user_id,
        registered_by_user_id=actor_user_id,
    )
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.created",
        target_type="model",
        target_id=str(created["model_id"]),
        payload={"owner_type": owner_type, "backend_kind": backend_kind, "visibility_scope": visibility_scope},
    )
    return serialize_model(created)


def register_existing_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    _ = config
    row = modelops_repo.get_model(database_url, model_id)
    if row is None:
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="create")
    lifecycle_state = str(row.get("lifecycle_state", "")).strip().lower()
    if lifecycle_state not in {"created", "unregistered"}:
        raise ModelOpsError("invalid_state_transition", "Model cannot be registered from its current state", status_code=409)
    updated = modelops_repo.set_lifecycle_state(database_url, model_id=model_id, lifecycle_state="registered")
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.registered",
        target_type="model",
        target_id=model_id,
        payload={},
    )
    return serialize_model(updated or row)


def activate_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="activate")
    if not bool(row.get("is_validation_current")) or str(row.get("last_validation_status", "")).strip().lower() != modelops_repo.VALIDATION_SUCCESS:
        raise ModelOpsError("validation_failed", "Model must be successfully validated before activation", status_code=409)
    if resolve_runtime_profile(database_url) == "offline" and str(row.get("runtime_mode_policy", "")).strip().lower() == "online_only":
        raise ModelOpsError("offline_not_allowed", "Cloud models cannot be activated for offline runtime", status_code=409)
    updated = modelops_repo.activate_model(database_url, model_id=model_id)
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.activated",
        target_type="model",
        target_id=model_id,
        payload={},
    )
    return serialize_model(updated or row)


def deactivate_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="deactivate")
    updated = modelops_repo.deactivate_model(database_url, model_id=model_id)
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.deactivated",
        target_type="model",
        target_id=model_id,
        payload={},
    )
    return serialize_model(updated or row)


def unregister_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="unregister")
    if str(row.get("lifecycle_state", "")).strip().lower() == modelops_repo.LIFECYCLE_ACTIVE:
        raise ModelOpsError("invalid_state_transition", "Active models must be deactivated before unregistering", status_code=409)
    updated = modelops_repo.set_lifecycle_state(database_url, model_id=model_id, lifecycle_state=modelops_repo.LIFECYCLE_UNREGISTERED)
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.unregistered",
        target_type="model",
        target_id=model_id,
        payload={},
    )
    return serialize_model(updated or row)


def delete_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> None:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="delete")
    if str(row.get("lifecycle_state", "")).strip().lower() != modelops_repo.LIFECYCLE_UNREGISTERED:
        raise ModelOpsError("invalid_state_transition", "Model must be unregistered before deletion", status_code=409)
    if count_deployment_bindings_for_served_model(database_url, model_id=model_id) > 0:
        raise ModelOpsError("dependencies_unsatisfied", "Model is still referenced by a deployment binding", status_code=409)
    deleted = modelops_repo.delete_model(database_url, model_id=model_id)
    if not deleted:
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.deleted",
        target_type="model",
        target_id=model_id,
        payload={},
    )
