from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from flask import g, jsonify, request

from ..authz import require_role
from ..services.connectivity_policy import ConnectivityPolicyError

DISCOVERY_LIMIT_MIN = 1
DISCOVERY_LIMIT_MAX = 50
HF_TASK_BY_TASK_KEY = {
    "llm": "text-generation",
    "embeddings": "feature-extraction",
}


def register_modelops_local_routes(
    bp,
    *,
    config_getter,
    json_error_fn,
    modelops_repo,
    serialize_catalog_item_fn,
    serialize_local_artifact_fn,
    append_audit_event_fn,
    list_scope_assignments_fn=None,
    assert_internet_allowed_fn,
    discover_hf_models_fn,
    get_hf_model_details_fn,
    resolve_target_dir_fn,
    parse_patterns_fn,
    create_download_job_fn,
    get_download_job_fn,
    list_download_jobs_fn,
    serialize_download_job_fn,
    ensure_download_worker_started_fn,
):
    @bp.get("/v1/modelops/catalog")
    @require_role("superadmin")
    def list_modelops_catalog_route():
        rows = modelops_repo.list_catalog_models(config_getter().database_url)
        return jsonify({"models": [serialize_catalog_item_fn(row) for row in rows]}), 200

    @bp.get("/v1/modelops/local-artifacts")
    @require_role("superadmin")
    def list_modelops_local_artifacts_route():
        rows = modelops_repo.list_local_artifacts(config_getter().database_url)
        return jsonify({"artifacts": [serialize_local_artifact_fn(row) for row in rows]}), 200

    @bp.post("/v1/modelops/catalog")
    @require_role("superadmin")
    def create_modelops_catalog_route():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return json_error_fn(400, "invalid_payload", "Expected JSON object")

        name = str(payload.get("name", "")).strip()
        provider = str(payload.get("provider", "custom")).strip().lower() or "custom"
        source_id = str(payload.get("source_id", "")).strip() or None
        local_path = str(payload.get("local_path", "")).strip() or None
        task_key = str(payload.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
        category = str(payload.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

        if not name:
            return json_error_fn(400, "invalid_name", "name is required")
        if provider not in {"huggingface", "local", "custom"}:
            return json_error_fn(400, "invalid_provider", "provider must be huggingface, local, or custom")
        if provider == "local" and not local_path:
            return json_error_fn(400, "invalid_local_path", "local_path is required for local provider")
        if provider == "local" and local_path:
            storage_root = Path(config_getter().model_storage_root).resolve()
            candidate = Path(local_path).expanduser()
            if not candidate.is_absolute():
                candidate = storage_root / candidate
            candidate_resolved = candidate.resolve()
            if storage_root != candidate_resolved and storage_root not in candidate_resolved.parents:
                return json_error_fn(400, "invalid_local_path", "local_path must be under MODEL_STORAGE_ROOT")
            local_path = str(candidate_resolved)

        if provider == "huggingface" and source_id:
            try:
                resolved_local_path = resolve_target_dir_fn(config_getter().model_storage_root, source_id)
                if local_path is None:
                    local_path = resolved_local_path
            except ValueError:
                return json_error_fn(400, "invalid_source_id", "Invalid source_id")

        model_id = str(payload.get("id", "")).strip() or (source_id or name.lower().replace(" ", "-")).replace("/", "--")
        row = modelops_repo.upsert_model_record(
            config_getter().database_url,
            model_id=model_id,
            node_id=config_getter().modelops_node_id,
            name=name,
            provider=provider,
            task_key=task_key,
            category=category,
            backend_kind="local",
            source_kind="hf_import" if provider == "huggingface" else "local_folder",
            availability="offline_ready",
            visibility_scope="platform",
            owner_type=modelops_repo.OWNER_PLATFORM,
            owner_user_id=None,
            provider_model_id=None,
            credential_id=None,
            source_id=source_id,
            local_path=local_path,
            status=str(payload.get("status", "available")).strip().lower() or "available",
            lifecycle_state=modelops_repo.LIFECYCLE_REGISTERED,
            metadata=metadata,
            comment=str(payload.get("comment", "")).strip() or None,
            model_size_billion=float(payload.get("model_size_billion")) if payload.get("model_size_billion") is not None else None,
            created_by_user_id=int(g.current_user["id"]),
            registered_by_user_id=int(g.current_user["id"]),
        )
        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="model.catalog_created",
            target_type="model",
            target_id=model_id,
            payload={"provider": provider, "task_key": task_key},
        )
        return jsonify({"model": serialize_catalog_item_fn(row)}), 201

    @bp.get("/v1/modelops/discovery/huggingface")
    @require_role("superadmin")
    def discover_modelops_huggingface_route():
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model discovery")
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))

        query = str(request.args.get("query", "")).strip()
        task_key = str(request.args.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
        task = str(request.args.get("task", "")).strip() or HF_TASK_BY_TASK_KEY.get(task_key, "text-generation")
        sort = str(request.args.get("sort", "downloads")).strip() or "downloads"
        limit_raw = str(request.args.get("limit", "10")).strip()
        try:
            limit = max(DISCOVERY_LIMIT_MIN, min(DISCOVERY_LIMIT_MAX, int(limit_raw)))
        except ValueError:
            return json_error_fn(400, "invalid_limit", "limit must be an integer")

        try:
            models = discover_hf_models_fn(
                database_url=config_getter().database_url,
                query=query,
                task=task,
                sort=sort,
                limit=limit,
                token=config_getter().hf_token,
            )
        except Exception as exc:  # noqa: BLE001
            return json_error_fn(502, "hf_discovery_failed", str(exc))
        return jsonify({"models": models}), 200

    @bp.get("/v1/modelops/discovery/huggingface/<path:source_id>")
    @require_role("superadmin")
    def get_modelops_huggingface_detail_route(source_id: str):
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model discovery")
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))

        if not source_id.strip():
            return json_error_fn(400, "invalid_source_id", "source_id is required")
        try:
            model = get_hf_model_details_fn(
                source_id.strip(),
                database_url=config_getter().database_url,
                token=config_getter().hf_token,
            )
        except Exception as exc:  # noqa: BLE001
            return json_error_fn(502, "hf_model_info_failed", str(exc))
        return jsonify({"model": model}), 200

    @bp.post("/v1/modelops/downloads")
    @require_role("superadmin")
    def start_modelops_download_route():
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model download")
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return json_error_fn(400, "invalid_payload", "Expected JSON object")

        source_id = str(payload.get("source_id", "")).strip()
        task_key = str(payload.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
        if not source_id:
            return json_error_fn(400, "invalid_source_id", "source_id is required")

        allow_patterns = parse_patterns_fn(payload.get("allow_patterns"))
        ignore_patterns = parse_patterns_fn(payload.get("ignore_patterns"))
        config = config_getter()

        try:
            target_dir = resolve_target_dir_fn(config.model_storage_root, source_id)
        except ValueError:
            return json_error_fn(400, "invalid_source_id", "Invalid source_id")

        model_id = source_id.replace("/", "--")
        display_name = str(payload.get("name", "")).strip() or source_id.split("/")[-1]
        category = str(payload.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
        metadata = {
            "source": "huggingface",
            "allow_patterns": allow_patterns or parse_patterns_fn(config.model_download_allow_patterns_default) or [],
            "ignore_patterns": ignore_patterns or parse_patterns_fn(config.model_download_ignore_patterns_default) or [],
        }

        modelops_repo.upsert_model_record(
            config.database_url,
            model_id=model_id,
            node_id=config.modelops_node_id,
            name=display_name,
            provider="huggingface",
            task_key=task_key,
            category=category,
            backend_kind="local",
            source_kind="hf_import",
            availability="offline_ready",
            visibility_scope="platform",
            owner_type=modelops_repo.OWNER_PLATFORM,
            owner_user_id=None,
            provider_model_id=None,
            credential_id=None,
            source_id=source_id,
            local_path=target_dir,
            status="downloading",
            lifecycle_state=modelops_repo.LIFECYCLE_CREATED,
            metadata=metadata,
            comment=None,
            model_size_billion=None,
            created_by_user_id=int(g.current_user["id"]),
            registered_by_user_id=int(g.current_user["id"]),
        )

        job_id = uuid4()
        created = create_download_job_fn(
            config.database_url,
            job_id=job_id,
            provider="huggingface",
            source_id=source_id,
            target_dir=target_dir,
            created_by_user_id=int(g.current_user["id"]),
        )
        ensure_download_worker_started_fn()
        return jsonify({"job": serialize_download_job_fn(created)}), 202

    @bp.get("/v1/modelops/downloads")
    @require_role("superadmin")
    def list_modelops_downloads_route():
        status = str(request.args.get("status", "")).strip().lower() or None
        rows = list_download_jobs_fn(config_getter().database_url, status=status)
        return jsonify({"jobs": [serialize_download_job_fn(row) for row in rows]}), 200

    @bp.get("/v1/modelops/downloads/<job_id>")
    @require_role("superadmin")
    def get_modelops_download_route(job_id: str):
        try:
            UUID(job_id)
        except ValueError:
            return json_error_fn(400, "invalid_job_id", "job_id must be a UUID")

        row = get_download_job_fn(config_getter().database_url, job_id)
        if row is None:
            return json_error_fn(404, "job_not_found", "Download job not found")
        return jsonify({"job": serialize_download_job_fn(row)}), 200
