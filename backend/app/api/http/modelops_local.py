from __future__ import annotations

from flask import g, jsonify, request

from ...application.modelops_local_service import (
    normalize_catalog_payload,
    normalize_discovery_request,
    normalize_download_request,
    validate_job_id,
)
from ...authz import require_role
from ...services.connectivity_policy import ConnectivityPolicyError
from ...services.modelops_common import ModelOpsError


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
    _ = (list_scope_assignments_fn, resolve_target_dir_fn, parse_patterns_fn)

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
        try:
            catalog_request = normalize_catalog_payload(
                request.get_json(silent=True),
                model_storage_root=config_getter().model_storage_root,
            )
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        row = modelops_repo.upsert_model_record(
            config_getter().database_url,
            model_id=str(catalog_request["model_id"]),
            node_id=config_getter().modelops_node_id,
            name=str(catalog_request["name"]),
            provider=str(catalog_request["provider"]),
            task_key=str(catalog_request["task_key"]),
            category=str(catalog_request["category"]),
            backend_kind="local",
            source_kind=str(catalog_request["source_kind"]),
            availability="offline_ready",
            visibility_scope="platform",
            owner_type=modelops_repo.OWNER_PLATFORM,
            owner_user_id=None,
            provider_model_id=None,
            credential_id=None,
            source_id=catalog_request["source_id"],
            local_path=catalog_request["local_path"],
            status=str(catalog_request["status"]),
            lifecycle_state=modelops_repo.LIFECYCLE_REGISTERED,
            metadata=dict(catalog_request["metadata"]),
            comment=catalog_request["comment"],
            model_size_billion=catalog_request["model_size_billion"],
            created_by_user_id=int(g.current_user["id"]),
            registered_by_user_id=int(g.current_user["id"]),
        )
        append_audit_event_fn(
            config_getter().database_url,
            actor_user_id=int(g.current_user["id"]),
            event_type="model.catalog_created",
            target_type="model",
            target_id=str(catalog_request["model_id"]),
            payload={"provider": catalog_request["provider"], "task_key": catalog_request["task_key"]},
        )
        return jsonify({"model": serialize_catalog_item_fn(row)}), 201

    @bp.get("/v1/modelops/discovery/huggingface")
    @require_role("superadmin")
    def discover_modelops_huggingface_route():
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model discovery")
            discovery_request = normalize_discovery_request(
                query=request.args.get("query"),
                task_key=request.args.get("task_key"),
                task=request.args.get("task"),
                sort=request.args.get("sort"),
                limit=request.args.get("limit"),
                offset=request.args.get("offset"),
            )
            models = discover_hf_models_fn(
                database_url=config_getter().database_url,
                query=str(discovery_request["query"]),
                task=str(discovery_request["task"]),
                sort=str(discovery_request["sort"]),
                limit=int(discovery_request["limit"]),
                offset=int(discovery_request["offset"]),
                token=config_getter().hf_token,
            )
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        except Exception as exc:  # noqa: BLE001
            return json_error_fn(502, "hf_discovery_failed", str(exc))
        return jsonify({"models": models}), 200

    @bp.get("/v1/modelops/discovery/huggingface/<path:source_id>")
    @require_role("superadmin")
    def get_modelops_huggingface_detail_route(source_id: str):
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model discovery")
            if not source_id.strip():
                raise ModelOpsError("invalid_source_id", "source_id is required", status_code=400)
            model = get_hf_model_details_fn(
                source_id.strip(),
                database_url=config_getter().database_url,
                token=config_getter().hf_token,
            )
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)
        except Exception as exc:  # noqa: BLE001
            return json_error_fn(502, "hf_model_info_failed", str(exc))
        return jsonify({"model": model}), 200

    @bp.post("/v1/modelops/downloads")
    @require_role("superadmin")
    def start_modelops_download_route():
        try:
            assert_internet_allowed_fn(config_getter().database_url, "Model download")
            download_request = normalize_download_request(
                request.get_json(silent=True),
                config=config_getter(),
                current_user_id=int(g.current_user["id"]),
            )
        except ConnectivityPolicyError as exc:
            return json_error_fn(exc.status_code, exc.code, str(exc))
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        modelops_repo.upsert_model_record(
            config_getter().database_url,
            model_id=str(download_request["model_id"]),
            node_id=config_getter().modelops_node_id,
            name=str(download_request["display_name"]),
            provider="huggingface",
            task_key=str(download_request["task_key"]),
            category=str(download_request["category"]),
            backend_kind="local",
            source_kind="hf_import",
            availability="offline_ready",
            visibility_scope="platform",
            owner_type=modelops_repo.OWNER_PLATFORM,
            owner_user_id=None,
            provider_model_id=None,
            credential_id=None,
            source_id=str(download_request["source_id"]),
            local_path=str(download_request["target_dir"]),
            status="downloading",
            lifecycle_state=modelops_repo.LIFECYCLE_CREATED,
            metadata=dict(download_request["metadata"]),
            comment=None,
            model_size_billion=None,
            created_by_user_id=int(download_request["created_by_user_id"]),
            registered_by_user_id=int(download_request["created_by_user_id"]),
        )

        created = create_download_job_fn(
            config_getter().database_url,
            job_id=download_request["job_id"],
            provider="huggingface",
            source_id=str(download_request["source_id"]),
            target_dir=str(download_request["target_dir"]),
            created_by_user_id=int(download_request["created_by_user_id"]),
        )
        ensure_download_worker_started_fn()
        return jsonify({"job": serialize_download_job_fn(created)}), 202

    @bp.get("/v1/modelops/downloads")
    @require_role("superadmin")
    def list_modelops_downloads_route():
        rows = list_download_jobs_fn(
            config_getter().database_url,
            status=str(request.args.get("status", "")).strip().lower() or None,
        )
        return jsonify({"jobs": [serialize_download_job_fn(row) for row in rows]}), 200

    @bp.get("/v1/modelops/downloads/<job_id>")
    @require_role("superadmin")
    def get_modelops_download_route(job_id: str):
        try:
            validate_job_id(job_id)
        except ModelOpsError as exc:
            return json_error_fn(exc.status_code, exc.code, exc.message, details=exc.details or None)

        row = get_download_job_fn(config_getter().database_url, job_id)
        if row is None:
            return json_error_fn(404, "job_not_found", "Download job not found")
        return jsonify({"job": serialize_download_job_fn(row)}), 200
