from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import get_active_credential_secret
from ..repositories.platform_control_plane import count_deployment_bindings_for_served_model
from .provider_validation import ProviderValidationError, validate_openai_compatible_model
from .runtime_profile_service import resolve_runtime_profile


logger = logging.getLogger(__name__)


class ModelOpsError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def serialize_model(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    artifact = row.get("artifact") if isinstance(row.get("artifact"), dict) else {}
    dependencies = row.get("dependencies") if isinstance(row.get("dependencies"), list) else []
    usage = row.get("usage_summary") if isinstance(row.get("usage_summary"), dict) else None
    return {
        "id": row.get("model_id"),
        "global_model_id": row.get("global_model_id"),
        "node_id": row.get("node_id"),
        "name": row.get("name"),
        "provider": row.get("provider"),
        "provider_model_id": row.get("provider_model_id"),
        "backend": row.get("backend_kind"),
        "hosting": row.get("hosting_kind"),
        "owner_type": row.get("owner_type"),
        "owner_user_id": row.get("owner_user_id"),
        "source_kind": row.get("source_kind"),
        "source": row.get("source"),
        "source_id": row.get("source_id"),
        "availability": row.get("availability"),
        "runtime_mode_policy": row.get("runtime_mode_policy"),
        "visibility_scope": row.get("visibility_scope"),
        "task_key": row.get("task_key"),
        "category": row.get("category"),
        "lifecycle_state": row.get("lifecycle_state"),
        "is_validation_current": bool(row.get("is_validation_current")),
        "last_validation_status": row.get("last_validation_status"),
        "last_validated_at": row.get("last_validated_at"),
        "validation_error": row.get("last_validation_error") or {},
        "model_version": row.get("model_version"),
        "revision": row.get("revision"),
        "checksum": row.get("checksum"),
        "model_size_billion": row.get("model_size_billion"),
        "comment": row.get("comment"),
        "metadata": metadata,
        "artifact": artifact,
        "dependencies": dependencies,
        "usage_summary": usage,
    }


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
    row = modelops_repo.get_model(database_url, model_id)
    if row is None:
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="create")
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


def _can_manage_model(row: dict[str, Any], *, actor_user_id: int, actor_role: str, action: str) -> None:
    normalized_role = actor_role.strip().lower()
    owner_type = str(row.get("owner_type", "")).strip().lower() or modelops_repo.infer_owner_type(row)
    owner_user_id = int(row.get("owner_user_id") or 0)
    is_owned_by_actor = owner_type == modelops_repo.OWNER_USER and owner_user_id == actor_user_id

    if normalized_role == "superadmin":
        return
    if normalized_role == "admin":
        if action in {"validate", "activate", "deactivate"}:
            return
        if action in {"list", "read"}:
            return
        raise ModelOpsError("forbidden", "Admins cannot perform this model lifecycle action", status_code=403)
    if normalized_role == "user":
        if is_owned_by_actor and action in {"read", "validate", "activate", "deactivate", "delete", "unregister"}:
            return
        if is_owned_by_actor and action == "create":
            return
    raise ModelOpsError("forbidden", "You do not have access to this model action", status_code=403)


def _get_accessible_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = modelops_repo.get_model(database_url, model_id)
    if row is None:
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    if actor_role == "superadmin":
        return row

    runtime_profile = resolve_runtime_profile(database_url)
    visible_models = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=False,
    )
    if not any(str(item.get("model_id")) == model_id.strip() for item in visible_models):
        raise ModelOpsError("not_found", "Model not found", status_code=404)
    return row

def list_models(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    require_active: bool = False,
    capability_key: str | None = None,
) -> list[dict[str, Any]]:
    runtime_profile = resolve_runtime_profile(database_url)
    rows = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=require_active,
        capability_key=capability_key,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = serialize_model(row)
        payload["usage_summary"] = modelops_repo.get_usage_summary(database_url, model_id=str(row["model_id"]))
        items.append(payload)
    return items


def get_model_detail(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    runtime_profile = resolve_runtime_profile(database_url)
    rows = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=False,
    )
    row = next((item for item in rows if str(item.get("model_id")) == model_id.strip()), None)
    if row is None:
        if actor_role == "superadmin":
            row = modelops_repo.get_model(database_url, model_id.strip())
        if row is None:
            raise ModelOpsError("not_found", "Model not found", status_code=404)
    payload = serialize_model(row)
    payload["validation_history"] = modelops_repo.list_validation_history(database_url, model_id=model_id)
    payload["usage_summary"] = modelops_repo.get_usage_summary(database_url, model_id=model_id)
    return payload


def get_model_usage(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    return {
        "model_id": model_id,
        "usage": modelops_repo.get_usage_summary(database_url, model_id=model_id),
    }


def get_model_validations(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    return {
        "model_id": model_id,
        "validations": modelops_repo.list_validation_history(database_url, model_id=model_id, limit=limit),
    }


def validate_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    trigger_reason: str = "manual",
) -> dict[str, Any]:
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")
    lifecycle_state = str(row.get("lifecycle_state", "")).strip().lower() or modelops_repo.LIFECYCLE_REGISTERED
    if lifecycle_state not in {modelops_repo.LIFECYCLE_REGISTERED, modelops_repo.LIFECYCLE_INACTIVE, modelops_repo.LIFECYCLE_VALIDATED, modelops_repo.LIFECYCLE_ACTIVE}:
        raise ModelOpsError("invalid_state_transition", "Model cannot be validated in its current state", status_code=409)

    validator_kind = "local_artifact_probe" if str(row.get("hosting_kind", "")).strip().lower() == "local" else "cloud_probe"
    config_fingerprint = modelops_repo.compute_config_fingerprint(row)

    if str(row.get("backend_kind", "")).strip().lower() == "external_api":
        credential_id = str(row.get("credential_id", "")).strip()
        if not credential_id:
            raise ModelOpsError("missing_config", "Cloud model is missing a credential", status_code=400)
        secret = get_active_credential_secret(
            database_url,
            credential_id=credential_id,
            requester_user_id=actor_user_id,
            requester_role=actor_role,
            encryption_key=config.model_credentials_encryption_key,
        )
        if secret is None:
            raise ModelOpsError("missing_config", "Active credential not found for model validation", status_code=400)
        try:
            validate_openai_compatible_model(
                api_base_url=str(secret.get("api_base_url") or ""),
                api_key=str(secret.get("api_key") or ""),
                model_id=str(row.get("provider_model_id") or ""),
            )
            validation = modelops_repo.append_validation(
                database_url,
                model_id=model_id,
                validator_kind=validator_kind,
                trigger_reason=trigger_reason,
                result=modelops_repo.VALIDATION_SUCCESS,
                summary="Cloud model validation succeeded",
                error_details={},
                config_fingerprint=config_fingerprint,
                validated_by_user_id=actor_user_id,
            )
        except ProviderValidationError as exc:
            validation = modelops_repo.append_validation(
                database_url,
                model_id=model_id,
                validator_kind=validator_kind,
                trigger_reason=trigger_reason,
                result=modelops_repo.VALIDATION_FAILURE,
                summary="Cloud model validation failed",
                error_details={"error": str(exc)},
                config_fingerprint=config_fingerprint,
                validated_by_user_id=actor_user_id,
            )
            raise ModelOpsError("validation_failed", "Cloud validation failed", status_code=409, details={"validation": validation}) from exc
    else:
        artifact = row.get("artifact") if isinstance(row.get("artifact"), dict) else {}
        storage_path = str(artifact.get("storage_path") or row.get("local_path") or "").strip()
        if not storage_path:
            raise ModelOpsError("missing_config", "Local model is missing an artifact path", status_code=400)
        exists = Path(storage_path).exists()
        if not exists:
            validation = modelops_repo.append_validation(
                database_url,
                model_id=model_id,
                validator_kind=validator_kind,
                trigger_reason=trigger_reason,
                result=modelops_repo.VALIDATION_FAILURE,
                summary="Local artifact validation failed",
                error_details={"error": "artifact_missing", "storage_path": storage_path},
                config_fingerprint=config_fingerprint,
                validated_by_user_id=actor_user_id,
            )
            raise ModelOpsError("validation_failed", "Local validation failed", status_code=409, details={"validation": validation})
        validation = modelops_repo.append_validation(
            database_url,
            model_id=model_id,
            validator_kind=validator_kind,
            trigger_reason=trigger_reason,
            result=modelops_repo.VALIDATION_SUCCESS,
            summary="Local artifact validation succeeded",
            error_details={},
            config_fingerprint=config_fingerprint,
            validated_by_user_id=actor_user_id,
        )

    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.validated",
        target_type="model",
        target_id=model_id,
        payload={"validator_kind": validator_kind, "result": validation.get("result")},
    )
    return {
        "model": serialize_model(modelops_repo.get_model(database_url, model_id) or row),
        "validation": validation,
    }


def activate_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="activate")
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
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="deactivate")
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
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="unregister")
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
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="delete")
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


def ensure_model_invokable(
    database_url: str,
    *,
    config: AuthConfig,
    user_id: int,
    user_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_model_detail(
        database_url,
        config=config,
        actor_user_id=user_id,
        actor_role=user_role,
        model_id=model_id,
    )
    if row["lifecycle_state"] != "active":
        raise ModelOpsError("invalid_state_transition", "Model is not active", status_code=409)
    if not row["is_validation_current"] or row["last_validation_status"] != "success":
        raise ModelOpsError("validation_failed", "Model validation is not current", status_code=409)
    runtime_profile = resolve_runtime_profile(database_url)
    if runtime_profile != "online" and row["runtime_mode_policy"] == "online_only":
        raise ModelOpsError("offline_not_allowed", "Model is not available in offline mode", status_code=409)
    return row


def record_usage(
    database_url: str,
    *,
    model_id: str,
    user_id: int | None,
    usage_payload: dict[str, Any] | None,
    latency_ms: float,
) -> None:
    try:
        modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="calls", metric_value=1, request_count=1)
        modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="latency_ms", metric_value=latency_ms, request_count=0)
        usage_payload = usage_payload or {}
        prompt_tokens = usage_payload.get("prompt_tokens")
        completion_tokens = usage_payload.get("completion_tokens")
        if isinstance(prompt_tokens, (int, float)):
            modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="prompt_tokens", metric_value=float(prompt_tokens), request_count=0)
        if isinstance(completion_tokens, (int, float)):
            modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="completion_tokens", metric_value=float(completion_tokens), request_count=0)
    except Exception:
        logger.exception("Failed to record ModelOps usage for model %s", model_id)
        return


def measure_and_record_inference(
    database_url: str,
    *,
    model_id: str,
    user_id: int | None,
    callable_fn,
):
    started_at = perf_counter()
    payload, status_code = callable_fn()
    latency_ms = (perf_counter() - started_at) * 1000
    if status_code < 400 and isinstance(payload, dict):
        record_usage(
            database_url,
            model_id=model_id,
            user_id=user_id,
            usage_payload=payload.get("usage") if isinstance(payload.get("usage"), dict) else None,
            latency_ms=latency_ms,
        )
    return payload, status_code
