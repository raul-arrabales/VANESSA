from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from flask import Blueprint, g, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories import modelops as modelops_repo
from ..repositories.model_assignments import list_scope_assignments, upsert_scope_assignment
from ..repositories.model_credentials import create_credential, list_credentials_for_user, revoke_credential
from ..repositories.model_download_jobs import create_download_job, get_download_job, list_download_jobs
from ..services.connectivity_policy import ConnectivityPolicyError, assert_internet_allowed
from ..services.hf_discovery import discover_hf_models, get_hf_model_details
from ..services.model_download_worker import ensure_download_worker_started
from ..services.model_downloader import resolve_target_dir
from ..services.modelops_service import (
    ModelOpsError,
    activate_model,
    create_model,
    deactivate_model,
    delete_model,
    get_model_detail,
    get_model_tests,
    get_model_usage,
    get_model_validations,
    list_models,
    register_existing_model,
    run_model_test,
    unregister_model,
    validate_model,
)
from ..services.model_support import parse_patterns, serialize_assignment, serialize_download_job

bp = Blueprint("modelops", __name__)

_DISCOVERY_LIMIT_MIN = 1
_DISCOVERY_LIMIT_MAX = 50
_HF_TASK_BY_TASK_KEY = {
    "llm": "text-generation",
    "embeddings": "feature-extraction",
}


def _config():
    return get_auth_config()


def _json_error(status: int, code: str, message: str, *, details: dict | None = None):
    payload = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _serialize_credential(row: dict[str, object]) -> dict[str, object]:
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


def _serialize_catalog_item(row: dict[str, object]) -> dict[str, object]:
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


def _serialize_local_artifact(row: dict[str, object]) -> dict[str, object]:
    lifecycle_state = str(row.get("lifecycle_state", "")).strip().lower()
    artifact_status = str(row.get("artifact_status", "")).strip().lower()
    ready_for_registration = artifact_status == "ready" and lifecycle_state in {
        modelops_repo.LIFECYCLE_CREATED,
        modelops_repo.LIFECYCLE_UNREGISTERED,
    }

    if artifact_status == "ready":
        validation_hint = (
            "ready_to_register"
            if ready_for_registration
            else "artifact_ready"
        )
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


@bp.get("/v1/modelops/models")
@require_role("user")
def list_modelops_models_route():
    capability_key = str(request.args.get("capability", "")).strip().lower() or None
    eligible_only = str(request.args.get("eligible", "")).strip().lower() in {"1", "true", "yes"}
    try:
        models = list_models(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            require_active=eligible_only,
            capability_key=capability_key,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"models": models}), 200


@bp.post("/v1/modelops/models")
@require_role("user")
def create_modelops_model_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        model = create_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            payload=payload,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 201


@bp.get("/v1/modelops/models/<model_id>")
@require_role("user")
def get_modelops_model_route(model_id: str):
    try:
        model = get_model_detail(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 200


@bp.get("/v1/modelops/models/<model_id>/usage")
@require_role("user")
def get_modelops_model_usage_route(model_id: str):
    try:
        payload = get_model_usage(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.get("/v1/modelops/models/<model_id>/validations")
@require_role("user")
def get_modelops_model_validations_route(model_id: str):
    limit_raw = str(request.args.get("limit", "20")).strip()
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError:
        return _json_error(400, "invalid_limit", "limit must be an integer")
    try:
        payload = get_model_validations(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
            limit=limit,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/modelops/models/<model_id>/register")
@require_role("user")
def register_modelops_model_route(model_id: str):
    try:
        model = register_existing_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 200


@bp.post("/v1/modelops/models/<model_id>/validate")
@require_role("admin")
def validate_modelops_model_route(model_id: str):
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    try:
        result = validate_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
            trigger_reason="manual_after_test",
            test_run_id=str(payload.get("test_run_id", "")).strip() or None,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200


@bp.get("/v1/modelops/models/<model_id>/tests")
@require_role("admin")
def get_modelops_model_tests_route(model_id: str):
    limit_raw = str(request.args.get("limit", "10")).strip()
    try:
        limit = max(1, min(50, int(limit_raw)))
    except ValueError:
        return _json_error(400, "invalid_limit", "limit must be an integer")
    try:
        payload = get_model_tests(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
            limit=limit,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(payload), 200


@bp.post("/v1/modelops/models/<model_id>/test")
@require_role("admin")
def test_modelops_model_route(model_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")
    raw_inputs = payload.get("inputs")
    if not isinstance(raw_inputs, dict):
        return _json_error(400, "invalid_payload", "inputs must be an object")
    try:
        result = run_model_test(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
            inputs=raw_inputs,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify(result), 200


@bp.post("/v1/modelops/models/<model_id>/activate")
@require_role("user")
def activate_modelops_model_route(model_id: str):
    try:
        model = activate_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 200


@bp.post("/v1/modelops/models/<model_id>/deactivate")
@require_role("user")
def deactivate_modelops_model_route(model_id: str):
    try:
        model = deactivate_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 200


@bp.post("/v1/modelops/models/<model_id>/unregister")
@require_role("user")
def unregister_modelops_model_route(model_id: str):
    try:
        model = unregister_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"model": model}), 200


@bp.delete("/v1/modelops/models/<model_id>")
@require_role("user")
def delete_modelops_model_route(model_id: str):
    try:
        delete_model(
            _config().database_url,
            config=_config(),
            actor_user_id=int(g.current_user["id"]),
            actor_role=str(g.current_user.get("role", "user")),
            model_id=model_id,
        )
    except ModelOpsError as exc:
        return _json_error(exc.status_code, exc.code, exc.message, details=exc.details or None)
    return jsonify({"deleted": True, "model_id": model_id}), 200


@bp.get("/v1/modelops/credentials")
@require_role("user")
def list_modelops_credentials_route():
    rows = list_credentials_for_user(
        _config().database_url,
        requester_user_id=int(g.current_user["id"]),
        requester_role=str(g.current_user.get("role", "user")),
    )
    return jsonify({"credentials": [_serialize_credential(row) for row in rows]}), 200


@bp.post("/v1/modelops/credentials")
@require_role("user")
def create_modelops_credentials_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    current_user_id = int(g.current_user["id"])
    role = str(g.current_user.get("role", "user"))
    credential_scope = str(payload.get("credential_scope", "personal")).strip().lower() or "personal"
    if credential_scope == "platform" and role != "superadmin":
        return _json_error(403, "forbidden", "Only superadmin can create platform credentials")

    owner_user_id = current_user_id if credential_scope == "personal" else int(payload.get("owner_user_id", current_user_id))
    try:
        created = create_credential(
            _config().database_url,
            owner_user_id=owner_user_id,
            credential_scope=credential_scope,
            provider_slug=str(payload.get("provider", "openai_compatible")).strip().lower(),
            display_name=str(payload.get("display_name", "")).strip() or "credential",
            api_base_url=str(payload.get("api_base_url", "")).strip() or None,
            api_key=str(payload.get("api_key", "")).strip(),
            encryption_key=_config().model_credentials_encryption_key,
            created_by_user_id=current_user_id,
        )
    except ValueError as exc:
        return _json_error(400, str(exc), "Invalid credential payload")

    modelops_repo.append_audit_event(
        _config().database_url,
        actor_user_id=current_user_id,
        event_type="credential.created",
        target_type="credential",
        target_id=str(created["id"]),
        payload={"owner_user_id": owner_user_id, "credential_scope": credential_scope},
    )
    return jsonify({"credential": _serialize_credential(created)}), 201


@bp.delete("/v1/modelops/credentials/<credential_id>")
@require_role("user")
def delete_modelops_credential_route(credential_id: str):
    try:
        revoked = revoke_credential(
            _config().database_url,
            credential_id=credential_id,
            owner_user_id=int(g.current_user["id"]),
        )
    except ValueError:
        return _json_error(400, "invalid_credential_id", "credential_id must be a UUID")

    if revoked is None:
        return _json_error(404, "credential_not_found", "Credential not found")

    modelops_repo.append_audit_event(
        _config().database_url,
        actor_user_id=int(g.current_user["id"]),
        event_type="credential.revoked",
        target_type="credential",
        target_id=credential_id,
        payload={},
    )
    return jsonify({"credential": _serialize_credential(revoked)}), 200


@bp.get("/v1/modelops/catalog")
@require_role("superadmin")
def list_modelops_catalog_route():
    rows = modelops_repo.list_catalog_models(_config().database_url)
    return jsonify({"models": [_serialize_catalog_item(row) for row in rows]}), 200


@bp.get("/v1/modelops/local-artifacts")
@require_role("superadmin")
def list_modelops_local_artifacts_route():
    rows = modelops_repo.list_local_artifacts(_config().database_url)
    return jsonify({"artifacts": [_serialize_local_artifact(row) for row in rows]}), 200


@bp.post("/v1/modelops/catalog")
@require_role("superadmin")
def create_modelops_catalog_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    name = str(payload.get("name", "")).strip()
    provider = str(payload.get("provider", "custom")).strip().lower() or "custom"
    source_id = str(payload.get("source_id", "")).strip() or None
    local_path = str(payload.get("local_path", "")).strip() or None
    task_key = str(payload.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    category = str(payload.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
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

    if provider == "huggingface" and source_id:
        try:
            resolved_local_path = resolve_target_dir(_config().model_storage_root, source_id)
            if local_path is None:
                local_path = resolved_local_path
        except ValueError:
            return _json_error(400, "invalid_source_id", "Invalid source_id")

    model_id = str(payload.get("id", "")).strip() or (source_id or name.lower().replace(" ", "-")).replace("/", "--")
    row = modelops_repo.upsert_model_record(
        _config().database_url,
        model_id=model_id,
        node_id=_config().modelops_node_id,
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
    modelops_repo.append_audit_event(
        _config().database_url,
        actor_user_id=int(g.current_user["id"]),
        event_type="model.catalog_created",
        target_type="model",
        target_id=model_id,
        payload={"provider": provider, "task_key": task_key},
    )
    return jsonify({"model": _serialize_catalog_item(row)}), 201


@bp.get("/v1/modelops/sharing")
@require_role("admin")
def list_modelops_sharing_route():
    rows = list_scope_assignments(_config().database_url)
    return jsonify({"assignments": [serialize_assignment(row) for row in rows]}), 200


@bp.put("/v1/modelops/sharing")
@require_role("admin")
def update_modelops_sharing_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    scope = str(payload.get("scope", "")).strip().lower()
    model_ids = payload.get("model_ids")
    if not isinstance(model_ids, list):
        return _json_error(400, "invalid_model_ids", "model_ids must be an array")

    try:
        saved = upsert_scope_assignment(
            _config().database_url,
            scope=scope,
            model_ids=[str(item) for item in model_ids],
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ValueError:
        return _json_error(400, "invalid_scope", "scope must be user, admin, or superadmin")

    modelops_repo.append_audit_event(
        _config().database_url,
        actor_user_id=int(g.current_user["id"]),
        event_type="model.sharing_updated",
        target_type="model_scope_assignment",
        target_id=scope,
        payload={"model_ids": saved.get("model_ids") or []},
    )
    return jsonify({"assignment": serialize_assignment(saved)}), 200


@bp.get("/v1/modelops/discovery/huggingface")
@require_role("superadmin")
def discover_modelops_huggingface_route():
    try:
        assert_internet_allowed(_config().database_url, "Model discovery")
    except ConnectivityPolicyError as exc:
        return _json_error(exc.status_code, exc.code, str(exc))

    query = str(request.args.get("query", "")).strip()
    task_key = str(request.args.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    task = str(request.args.get("task", "")).strip() or _HF_TASK_BY_TASK_KEY.get(task_key, "text-generation")
    sort = str(request.args.get("sort", "downloads")).strip() or "downloads"
    limit_raw = str(request.args.get("limit", "10")).strip()
    try:
        limit = max(_DISCOVERY_LIMIT_MIN, min(_DISCOVERY_LIMIT_MAX, int(limit_raw)))
    except ValueError:
        return _json_error(400, "invalid_limit", "limit must be an integer")

    try:
        models = discover_hf_models(
            database_url=_config().database_url,
            query=query,
            task=task,
            sort=sort,
            limit=limit,
            token=_config().hf_token,
        )
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_discovery_failed", str(exc))
    return jsonify({"models": models}), 200


@bp.get("/v1/modelops/discovery/huggingface/<path:source_id>")
@require_role("superadmin")
def get_modelops_huggingface_detail_route(source_id: str):
    try:
        assert_internet_allowed(_config().database_url, "Model discovery")
    except ConnectivityPolicyError as exc:
        return _json_error(exc.status_code, exc.code, str(exc))

    if not source_id.strip():
        return _json_error(400, "invalid_source_id", "source_id is required")
    try:
        model = get_hf_model_details(
            source_id.strip(),
            database_url=_config().database_url,
            token=_config().hf_token,
        )
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_model_info_failed", str(exc))
    return jsonify({"model": model}), 200


@bp.post("/v1/modelops/downloads")
@require_role("superadmin")
def start_modelops_download_route():
    try:
        assert_internet_allowed(_config().database_url, "Model download")
    except ConnectivityPolicyError as exc:
        return _json_error(exc.status_code, exc.code, str(exc))

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    source_id = str(payload.get("source_id", "")).strip()
    task_key = str(payload.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    if not source_id:
        return _json_error(400, "invalid_source_id", "source_id is required")

    allow_patterns = parse_patterns(payload.get("allow_patterns"))
    ignore_patterns = parse_patterns(payload.get("ignore_patterns"))
    config = _config()

    try:
        target_dir = resolve_target_dir(config.model_storage_root, source_id)
    except ValueError:
        return _json_error(400, "invalid_source_id", "Invalid source_id")

    model_id = source_id.replace("/", "--")
    display_name = str(payload.get("name", "")).strip() or source_id.split("/")[-1]
    category = str(payload.get("category", "")).strip().lower() or modelops_repo.infer_category(task_key)
    metadata = {
        "source": "huggingface",
        "allow_patterns": allow_patterns or parse_patterns(config.model_download_allow_patterns_default) or [],
        "ignore_patterns": ignore_patterns or parse_patterns(config.model_download_ignore_patterns_default) or [],
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


@bp.get("/v1/modelops/downloads")
@require_role("superadmin")
def list_modelops_downloads_route():
    status = str(request.args.get("status", "")).strip().lower() or None
    rows = list_download_jobs(_config().database_url, status=status)
    return jsonify({"jobs": [serialize_download_job(row) for row in rows]}), 200


@bp.get("/v1/modelops/downloads/<job_id>")
@require_role("superadmin")
def get_modelops_download_route(job_id: str):
    try:
        UUID(job_id)
    except ValueError:
        return _json_error(400, "invalid_job_id", "job_id must be a UUID")

    row = get_download_job(_config().database_url, job_id)
    if row is None:
        return _json_error(404, "job_not_found", "Download job not found")
    return jsonify({"job": serialize_download_job(row)}), 200
