from __future__ import annotations

from typing import Any


def serialize_model_definition(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_id": row.get("model_id"),
        "provider": row.get("provider"),
        "metadata": row.get("metadata") or {},
        "provider_config_ref": row.get("provider_config_ref"),
    }


def serialize_catalog_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("model_id"),
        "name": row.get("name"),
        "provider": row.get("provider"),
        "source_id": row.get("source_id"),
        "local_path": row.get("local_path"),
        "status": row.get("status"),
        "model_type": row.get("model_type"),
        "metadata": row.get("metadata") or {},
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def serialize_assignment(row: dict[str, Any]) -> dict[str, Any]:
    model_ids_raw = row.get("model_ids") or []
    return {
        "scope": row.get("scope"),
        "model_ids": [str(item) for item in model_ids_raw if str(item).strip()],
    }


def serialize_download_job(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": str(row.get("id")),
        "provider": row.get("provider"),
        "source_id": row.get("source_id"),
        "target_dir": row.get("target_dir"),
        "model_id": row.get("model_id"),
        "status": row.get("status"),
        "error_message": row.get("error_message"),
        "started_at": row.get("started_at").isoformat() if row.get("started_at") else None,
        "finished_at": row.get("finished_at").isoformat() if row.get("finished_at") else None,
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def parse_patterns(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        patterns = [token.strip() for token in value.split(",") if token.strip()]
        return patterns if patterns else None
    if isinstance(value, list):
        patterns = [str(token).strip() for token in value if str(token).strip()]
        return patterns if patterns else None
    return None


def model_id_from_source(source_id: str) -> str:
    return source_id.strip().replace("/", "--")
