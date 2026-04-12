from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ..repositories import modelops as modelops_repo
from ..repositories.model_download_jobs import (
    create_download_job as _create_download_job,
    get_download_job as _get_download_job,
    list_download_jobs as _list_download_jobs,
)
from ..services.connectivity_policy import assert_internet_allowed as _assert_internet_allowed
from ..services.hf_discovery import discover_hf_models as _discover_hf_models, get_hf_model_details as _get_hf_model_details
from ..services.model_downloader import resolve_target_dir as _resolve_target_dir
from ..services.model_download_worker import ensure_download_worker_started as _ensure_download_worker_started
from ..services.model_support import parse_patterns as _parse_patterns
from ..services.modelops_common import ModelOpsError

DISCOVERY_LIMIT_MIN = 1
DISCOVERY_LIMIT_MAX = 50
DISCOVERY_OFFSET_MIN = 0
DISCOVERY_OFFSET_MAX = 500
HF_TASK_BY_TASK_KEY = {
    "llm": "text-generation",
    "embeddings": "feature-extraction",
}


def require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelOpsError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def list_catalog_models(database_url: str):
    return modelops_repo.list_catalog_models(database_url)


def list_local_artifacts(database_url: str):
    return modelops_repo.list_local_artifacts(database_url)


def append_audit_event(database_url: str, **kwargs) -> None:
    modelops_repo.append_audit_event(database_url, **kwargs)


def assert_internet_allowed(database_url: str, operation: str) -> None:
    _assert_internet_allowed(database_url, operation)


def discover_hf_models(*, database_url: str, query: str, task: str, sort: str, limit: int, offset: int = 0, token: str | None = None):
    return _discover_hf_models(
        database_url=database_url,
        query=query,
        task=task,
        sort=sort,
        limit=limit,
        offset=offset,
        token=token,
    )


def get_hf_model_details(source_id: str, *, database_url: str, token: str | None = None):
    return _get_hf_model_details(source_id, database_url=database_url, token=token)


def resolve_target_dir(storage_root: str, source_id: str) -> str:
    try:
        return _resolve_target_dir(storage_root, source_id)
    except ValueError as exc:
        raise ModelOpsError("invalid_source_id", "Invalid source_id", status_code=400) from exc


def parse_patterns(value: Any) -> list[str] | None:
    return _parse_patterns(value)


def create_download_job(database_url: str, *, job_id, provider: str, source_id: str, target_dir: str, created_by_user_id: int):
    return _create_download_job(
        database_url,
        job_id=job_id,
        provider=provider,
        source_id=source_id,
        target_dir=target_dir,
        created_by_user_id=created_by_user_id,
    )


def get_download_job(database_url: str, job_id: str):
    return _get_download_job(database_url, job_id)


def list_download_jobs(database_url: str, *, status: str | None = None, limit: int = 50):
    return _list_download_jobs(database_url, status=status, limit=limit)


def ensure_download_worker_started() -> None:
    _ensure_download_worker_started()


def parse_discovery_limit(value: Any) -> int:
    raw_value = str(value if value is not None else 10).strip() or "10"
    try:
        return max(DISCOVERY_LIMIT_MIN, min(DISCOVERY_LIMIT_MAX, int(raw_value)))
    except ValueError as exc:
        raise ModelOpsError("invalid_limit", "limit must be an integer", status_code=400) from exc


def parse_discovery_offset(value: Any) -> int:
    raw_value = str(value if value is not None else 0).strip() or "0"
    try:
        return max(DISCOVERY_OFFSET_MIN, min(DISCOVERY_OFFSET_MAX, int(raw_value)))
    except ValueError as exc:
        raise ModelOpsError("invalid_offset", "offset must be an integer", status_code=400) from exc


def normalize_discovery_request(*, query: Any, task_key: Any, task: Any, sort: Any, limit: Any, offset: Any = None) -> dict[str, object]:
    normalized_task_key = str(task_key or "").strip().lower() or modelops_repo.TASK_LLM
    normalized_task = str(task or "").strip() or HF_TASK_BY_TASK_KEY.get(normalized_task_key, "text-generation")
    return {
        "query": str(query or "").strip(),
        "task_key": normalized_task_key,
        "task": normalized_task,
        "sort": str(sort or "downloads").strip() or "downloads",
        "limit": parse_discovery_limit(limit),
        "offset": parse_discovery_offset(offset),
    }


def normalize_catalog_payload(payload: Any, *, model_storage_root: str) -> dict[str, object]:
    body = require_json_object(payload)
    name = str(body.get("name", "")).strip()
    provider = str(body.get("provider", "custom")).strip().lower() or "custom"
    source_id = str(body.get("source_id", "")).strip() or None
    local_path = str(body.get("local_path", "")).strip() or None
    task_key = str(body.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    category = str(body.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    if not name:
        raise ModelOpsError("invalid_name", "name is required", status_code=400)
    if provider not in {"huggingface", "local", "custom"}:
        raise ModelOpsError("invalid_provider", "provider must be huggingface, local, or custom", status_code=400)
    if provider == "local" and not local_path:
        raise ModelOpsError("invalid_local_path", "local_path is required for local provider", status_code=400)

    if provider == "local" and local_path:
        storage_root = Path(model_storage_root).resolve()
        candidate = Path(local_path).expanduser()
        if not candidate.is_absolute():
            candidate = storage_root / candidate
        candidate_resolved = candidate.resolve()
        if storage_root != candidate_resolved and storage_root not in candidate_resolved.parents:
            raise ModelOpsError("invalid_local_path", "local_path must be under MODEL_STORAGE_ROOT", status_code=400)
        local_path = str(candidate_resolved)

    if provider == "huggingface" and source_id and local_path is None:
        local_path = resolve_target_dir(model_storage_root, source_id)

    model_id = str(body.get("id", "")).strip() or (source_id or name.lower().replace(" ", "-")).replace("/", "--")
    return {
        "model_id": model_id,
        "name": name,
        "provider": provider,
        "source_id": source_id,
        "local_path": local_path,
        "task_key": task_key,
        "category": category,
        "metadata": metadata,
        "status": str(body.get("status", "available")).strip().lower() or "available",
        "comment": str(body.get("comment", "")).strip() or None,
        "model_size_billion": float(body.get("model_size_billion")) if body.get("model_size_billion") is not None else None,
        "source_kind": "hf_import" if provider == "huggingface" else "local_folder",
    }


def normalize_download_request(payload: Any, *, config, current_user_id: int) -> dict[str, object]:
    body = require_json_object(payload)
    source_id = str(body.get("source_id", "")).strip()
    if not source_id:
        raise ModelOpsError("invalid_source_id", "source_id is required", status_code=400)

    task_key = str(body.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    target_dir = resolve_target_dir(config.model_storage_root, source_id)
    allow_patterns = parse_patterns(body.get("allow_patterns"))
    ignore_patterns = parse_patterns(body.get("ignore_patterns"))
    model_id = source_id.replace("/", "--")
    display_name = str(body.get("name", "")).strip() or source_id.split("/")[-1]
    category = str(body.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
    metadata = {
        "source": "huggingface",
        "allow_patterns": allow_patterns or parse_patterns(config.model_download_allow_patterns_default) or [],
        "ignore_patterns": ignore_patterns or parse_patterns(config.model_download_ignore_patterns_default) or [],
    }
    return {
        "job_id": uuid4(),
        "source_id": source_id,
        "task_key": task_key,
        "target_dir": target_dir,
        "model_id": model_id,
        "display_name": display_name,
        "category": category,
        "metadata": metadata,
        "created_by_user_id": current_user_id,
    }


def validate_job_id(job_id: str) -> None:
    try:
        UUID(job_id)
    except ValueError as exc:
        raise ModelOpsError("invalid_job_id", "job_id must be a UUID", status_code=400) from exc
