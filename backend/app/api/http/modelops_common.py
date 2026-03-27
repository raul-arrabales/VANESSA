from __future__ import annotations

from ...config import get_auth_config
from ...repositories import modelops as modelops_repo


def config():
    return get_auth_config()


def json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    from flask import jsonify

    return jsonify(payload), status


def serialize_credential(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row.get("id")),
        "owner_user_id": row.get("owner_user_id"),
        "credential_scope": row.get("credential_scope"),
        "provider": row.get("provider_slug"),
        "display_name": row.get("display_name"),
        "api_base_url": row.get("api_base_url"),
        "api_key_last4": row.get("api_key_last4"),
        "is_active": bool(row.get("is_active")),
        "revoked_at": row.get("revoked_at"),
    }


def serialize_catalog_item(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row.get("model_id"),
        "name": row.get("name"),
        "provider": row.get("provider"),
        "source_id": row.get("source_id"),
        "local_path": row.get("local_path"),
        "status": row.get("status"),
        "task_key": row.get("task_key"),
        "category": row.get("category"),
        "hosting_kind": row.get("hosting_kind"),
        "lifecycle_state": row.get("lifecycle_state"),
        "is_validation_current": bool(row.get("is_validation_current")),
        "last_validation_status": row.get("last_validation_status"),
        "metadata": row.get("metadata") or {},
    }


def serialize_local_artifact(row: dict[str, object]) -> dict[str, object]:
    lifecycle_state = str(row.get("lifecycle_state", "")).strip().lower()
    artifact_status = str(row.get("artifact_status", "")).strip().lower()
    ready_for_registration = artifact_status == "ready" and lifecycle_state in {
        modelops_repo.LIFECYCLE_CREATED,
        modelops_repo.LIFECYCLE_UNREGISTERED,
    }

    if artifact_status == "ready":
        validation_hint = "ready_to_register" if ready_for_registration else "artifact_ready"
    elif artifact_status:
        validation_hint = f"artifact_{artifact_status}"
    else:
        validation_hint = "artifact_unknown"

    linked_model_id = None
    if lifecycle_state not in {
        modelops_repo.LIFECYCLE_CREATED,
        modelops_repo.LIFECYCLE_UNREGISTERED,
    }:
        linked_model_id = str(row.get("model_id"))

    suggested_model_id = str(row.get("model_id")) if ready_for_registration else None

    return {
        "artifact_id": f"{row.get('model_id')}:{row.get('artifact_type') or 'weights'}",
        "artifact_type": row.get("artifact_type") or "weights",
        "name": row.get("name"),
        "source_id": row.get("source_id"),
        "storage_path": row.get("storage_path"),
        "artifact_status": row.get("artifact_status"),
        "provenance": row.get("provenance"),
        "checksum": row.get("checksum"),
        "linked_model_id": linked_model_id,
        "suggested_model_id": suggested_model_id,
        "task_key": row.get("task_key"),
        "category": row.get("category"),
        "provider": row.get("provider"),
        "lifecycle_state": row.get("lifecycle_state"),
        "ready_for_registration": ready_for_registration,
        "validation_hint": validation_hint,
        "runtime_requirements": row.get("runtime_requirements") or {},
        "metadata": row.get("metadata") or {},
    }
