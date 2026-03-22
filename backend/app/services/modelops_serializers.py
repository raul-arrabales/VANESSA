from __future__ import annotations

from typing import Any


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


def serialize_model_test_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "model_id": row.get("model_id"),
        "task_key": row.get("task_key"),
        "result": row.get("result"),
        "summary": row.get("summary"),
        "input_payload": row.get("input_payload") or {},
        "output_payload": row.get("output_payload") or {},
        "error_details": row.get("error_details") or {},
        "latency_ms": row.get("latency_ms"),
        "config_fingerprint": row.get("config_fingerprint"),
        "tested_by_user_id": row.get("tested_by_user_id"),
        "created_at": row.get("created_at"),
    }
