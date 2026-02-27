from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories.model_catalog import (
    create_model_catalog_item,
    list_model_catalog,
    upsert_model_catalog_item,
)
from ..repositories.model_download_jobs import create_download_job, get_download_job, list_download_jobs
from ..services.hf_discovery import discover_hf_models, get_hf_model_details
from ..services.legacy_models_support import model_id_from_source, parse_patterns, serialize_catalog_item, serialize_download_job
from ..services.model_downloader import resolve_target_dir
from ..services.model_download_worker import ensure_download_worker_started
from ..services.runtime_profile_service import internet_allowed, resolve_runtime_profile

bp = Blueprint("model_catalog_v1", __name__)

_DISCOVERY_LIMIT_MIN = 1
_DISCOVERY_LIMIT_MAX = 50


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _config():
    return get_auth_config()


@bp.get("/v1/models/catalog")
@require_role("superadmin")
def list_catalog_v1():
    rows = list_model_catalog(_config().database_url)
    return jsonify({"models": [serialize_catalog_item(row) for row in rows]}), 200


@bp.post("/v1/models/catalog")
@require_role("superadmin")
def create_catalog_item_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    name = str(payload.get("name", "")).strip()
    provider = str(payload.get("provider", "custom")).strip().lower() or "custom"
    source_id = str(payload.get("source_id", "")).strip() or None
    local_path = str(payload.get("local_path", "")).strip() or None
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    if not name:
        return _json_error(400, "invalid_name", "name is required")
    if provider not in {"huggingface", "local", "custom"}:
        return _json_error(400, "invalid_provider", "provider must be huggingface, local, or custom")
    if provider == "local" and not local_path:
        return _json_error(400, "invalid_local_path", "local_path is required for local provider")
    if provider == "local" and local_path:
        storage_root = Path(_config().model_storage_root).resolve()
        candidate = Path(local_path).expanduser()
        if not candidate.is_absolute():
            candidate = storage_root / candidate
        candidate_resolved = candidate.resolve()
        if storage_root != candidate_resolved and storage_root not in candidate_resolved.parents:
            return _json_error(400, "invalid_local_path", "local_path must be under MODEL_STORAGE_ROOT")
        local_path = str(candidate_resolved)

    model_id = str(payload.get("id", "")).strip() or model_id_from_source(source_id or name.lower().replace(" ", "-"))

    if provider == "huggingface" and source_id:
        try:
            resolved_local_path = resolve_target_dir(_config().model_storage_root, source_id)
            if local_path is None:
                local_path = resolved_local_path
        except ValueError:
            return _json_error(400, "invalid_source_id", "Invalid source_id")

    try:
        created = create_model_catalog_item(
            _config().database_url,
            model_id=model_id,
            name=name,
            provider=provider,
            source_id=source_id,
            local_path=local_path,
            status=str(payload.get("status", "available")),
            metadata=metadata,
            created_by_user_id=int(g.current_user["id"]),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "duplicate_model":
            return _json_error(409, "duplicate_model", "model id already exists")
        return _json_error(400, code, "Invalid model catalog payload")

    return jsonify({"model": serialize_catalog_item(created)}), 201


@bp.get("/v1/models/discovery/huggingface")
@require_role("superadmin")
def discover_models_huggingface_v1():
    runtime_profile = resolve_runtime_profile(_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    query = str(request.args.get("query", "")).strip()
    task = str(request.args.get("task", "text-generation")).strip() or "text-generation"
    sort = str(request.args.get("sort", "downloads")).strip() or "downloads"
    limit_raw = str(request.args.get("limit", "10")).strip()
    try:
        limit = int(limit_raw)
    except ValueError:
        return _json_error(400, "invalid_limit", "limit must be an integer")
    limit = max(_DISCOVERY_LIMIT_MIN, min(_DISCOVERY_LIMIT_MAX, limit))

    try:
        models = discover_hf_models(
            query=query,
            task=task,
            sort=sort,
            limit=limit,
            token=_config().hf_token,
        )
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_discovery_failed", str(exc))

    return jsonify({"models": models}), 200


@bp.get("/v1/models/discovery/huggingface/<path:source_id>")
@require_role("superadmin")
def get_discovered_model_huggingface_v1(source_id: str):
    runtime_profile = resolve_runtime_profile(_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    if not source_id.strip():
        return _json_error(400, "invalid_source_id", "source_id is required")
    try:
        model = get_hf_model_details(source_id.strip(), token=_config().hf_token)
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_model_info_failed", str(exc))
    return jsonify({"model": model}), 200


@bp.post("/v1/models/downloads")
@require_role("superadmin")
def start_model_download_v1():
    runtime_profile = resolve_runtime_profile(_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model download disabled for runtime profile '{runtime_profile}'",
        )

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    source_id = str(payload.get("source_id", "")).strip()
    if not source_id:
        return _json_error(400, "invalid_source_id", "source_id is required")

    allow_patterns = parse_patterns(payload.get("allow_patterns"))
    ignore_patterns = parse_patterns(payload.get("ignore_patterns"))

    config = _config()
    try:
        target_dir = resolve_target_dir(config.model_storage_root, source_id)
    except ValueError:
        return _json_error(400, "invalid_source_id", "Invalid source_id")

    model_id = model_id_from_source(source_id)
    display_name = str(payload.get("name", "")).strip() or source_id.split("/")[-1]

    upsert_model_catalog_item(
        config.database_url,
        model_id=model_id,
        name=display_name,
        provider="huggingface",
        source_id=source_id,
        local_path=target_dir,
        status="downloading",
        metadata={
            "source": "huggingface",
            "allow_patterns": allow_patterns or parse_patterns(config.model_download_allow_patterns_default) or [],
            "ignore_patterns": ignore_patterns or parse_patterns(config.model_download_ignore_patterns_default) or [],
        },
        updated_by_user_id=int(g.current_user["id"]),
    )

    job_id = uuid4()
    created = create_download_job(
        config.database_url,
        job_id=job_id,
        provider="huggingface",
        source_id=source_id,
        target_dir=target_dir,
        created_by_user_id=int(g.current_user["id"]),
    )
    ensure_download_worker_started()
    return jsonify({"job": serialize_download_job(created)}), 202


@bp.get("/v1/models/downloads")
@require_role("superadmin")
def list_model_downloads_v1():
    status = str(request.args.get("status", "")).strip().lower() or None
    rows = list_download_jobs(_config().database_url, status=status, limit=50)
    return jsonify({"jobs": [serialize_download_job(row) for row in rows]}), 200


@bp.get("/v1/models/downloads/<job_id>")
@require_role("superadmin")
def get_model_download_v1(job_id: str):
    row = get_download_job(_config().database_url, job_id)
    if row is None:
        return _json_error(404, "download_job_not_found", "Download job not found")
    return jsonify({"job": serialize_download_job(row)}), 200
