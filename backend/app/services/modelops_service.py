from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import get_active_credential_secret
from ..repositories.platform_control_plane import count_deployment_bindings_for_served_model
from .platform_adapters import http_json_request
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
        if is_owned_by_actor and action in {"read", "activate", "deactivate", "delete", "unregister"}:
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


def get_model_tests(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    row = _get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    _can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")
    tests = modelops_repo.list_model_test_runs(database_url, model_id=model_id, limit=limit)
    return {
        "model_id": model_id,
        "tests": [serialize_model_test_run(item) for item in tests],
    }


def _normalize_model_test_inputs(task_key: str, inputs: dict[str, Any]) -> dict[str, str]:
    normalized_task = task_key.strip().lower()
    if normalized_task == modelops_repo.TASK_LLM:
        prompt = str(inputs.get("prompt", "")).strip()
        if not prompt:
            raise ModelOpsError("invalid_test_input", "prompt is required", status_code=400)
        return {"prompt": prompt}
    if normalized_task == modelops_repo.TASK_EMBEDDINGS:
        text = str(inputs.get("text", "")).strip()
        if not text:
            raise ModelOpsError("invalid_test_input", "text is required", status_code=400)
        return {"text": text}
    raise ModelOpsError("model_test_unsupported", "Testing is not supported for this model type", status_code=409)


def _credential_secret_for_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    row: dict[str, Any],
) -> dict[str, Any]:
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
        raise ModelOpsError("missing_config", "Active credential not found for model test", status_code=400)
    return secret


def _extract_llm_response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and str(item.get("type", "")).strip().lower() == "text":
                text = str(item.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)
    return ""


def _execute_cloud_llm_test(
    row: dict[str, Any],
    *,
    secret: dict[str, Any],
    prompt: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], float]:
    api_base_url = str(secret.get("api_base_url") or "").strip().rstrip("/")
    provider_model_id = str(row.get("provider_model_id") or "").strip()
    if not api_base_url:
        raise ModelOpsError("missing_config", "Cloud credential is missing api_base_url", status_code=400)
    if not provider_model_id:
        raise ModelOpsError("missing_config", "Cloud model is missing provider_model_id", status_code=400)

    request_payload = {
        "model": provider_model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 64,
    }
    started_at = perf_counter()
    payload, status_code = http_json_request(
        f"{api_base_url}/chat/completions",
        method="POST",
        payload=request_payload,
        headers={
            "Authorization": f"Bearer {str(secret.get('api_key') or '').strip()}",
        },
        timeout_seconds=8.0,
    )
    latency_ms = (perf_counter() - started_at) * 1000
    response_payload = payload if isinstance(payload, dict) else {}
    if payload is None or status_code >= 400:
        message = str(response_payload.get("message") or response_payload.get("error") or "Cloud LLM test failed")
        raise ModelOpsError(
            "model_test_failed",
            message,
            status_code=409,
            details={
                "summary": "Cloud LLM test failed",
                "output_payload": response_payload,
                "error_details": {"status_code": status_code, "message": message},
                "latency_ms": latency_ms,
            },
        )
    response_text = _extract_llm_response_text(response_payload)
    result_payload = {
        "kind": modelops_repo.TASK_LLM,
        "success": True,
        "response_text": response_text,
        "latency_ms": latency_ms,
        "metadata": {
            "model": provider_model_id,
            "status_code": status_code,
        },
    }
    return "Cloud LLM test succeeded", request_payload, response_payload, result_payload, latency_ms


def _execute_cloud_embeddings_test(
    row: dict[str, Any],
    *,
    secret: dict[str, Any],
    text: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], float]:
    api_base_url = str(secret.get("api_base_url") or "").strip().rstrip("/")
    provider_model_id = str(row.get("provider_model_id") or "").strip()
    if not api_base_url:
        raise ModelOpsError("missing_config", "Cloud credential is missing api_base_url", status_code=400)
    if not provider_model_id:
        raise ModelOpsError("missing_config", "Cloud model is missing provider_model_id", status_code=400)

    request_payload = {
        "model": provider_model_id,
        "input": [text],
    }
    started_at = perf_counter()
    payload, status_code = http_json_request(
        f"{api_base_url}/embeddings",
        method="POST",
        payload=request_payload,
        headers={
            "Authorization": f"Bearer {str(secret.get('api_key') or '').strip()}",
        },
        timeout_seconds=8.0,
    )
    latency_ms = (perf_counter() - started_at) * 1000
    response_payload = payload if isinstance(payload, dict) else {}
    if payload is None or status_code >= 400:
        message = str(response_payload.get("message") or response_payload.get("error") or "Cloud embeddings test failed")
        raise ModelOpsError(
            "model_test_failed",
            message,
            status_code=409,
            details={
                "summary": "Cloud embeddings test failed",
                "output_payload": response_payload,
                "error_details": {"status_code": status_code, "message": message},
                "latency_ms": latency_ms,
            },
        )

    data = response_payload.get("data")
    vectors = data if isinstance(data, list) else []
    first_vector = vectors[0].get("embedding") if vectors and isinstance(vectors[0], dict) else []
    dimension = len(first_vector) if isinstance(first_vector, list) else 0
    result_payload = {
        "kind": modelops_repo.TASK_EMBEDDINGS,
        "success": True,
        "dimension": dimension,
        "latency_ms": latency_ms,
        "vector_preview": first_vector[:8] if isinstance(first_vector, list) else [],
        "metadata": {
            "model": provider_model_id,
            "count": len(vectors),
            "status_code": status_code,
        },
    }
    return "Cloud embeddings test succeeded", request_payload, response_payload, result_payload, latency_ms


def run_model_test(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    inputs: dict[str, Any],
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
    if lifecycle_state not in {
        modelops_repo.LIFECYCLE_REGISTERED,
        modelops_repo.LIFECYCLE_VALIDATED,
        modelops_repo.LIFECYCLE_INACTIVE,
        modelops_repo.LIFECYCLE_ACTIVE,
    }:
        raise ModelOpsError("invalid_state_transition", "Model cannot be tested in its current state", status_code=409)

    task_key = str(row.get("task_key", "")).strip().lower() or modelops_repo.TASK_LLM
    normalized_inputs = _normalize_model_test_inputs(task_key, inputs)
    config_fingerprint = str(row.get("current_config_fingerprint") or modelops_repo.compute_config_fingerprint(row))
    runtime_profile = resolve_runtime_profile(database_url)
    backend_kind = str(row.get("backend_kind", "")).strip().lower()
    runtime_mode_policy = str(row.get("runtime_mode_policy", "")).strip().lower()

    if runtime_profile != "online" and runtime_mode_policy == "online_only":
        test_run = modelops_repo.append_model_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            result=modelops_repo.TEST_FAILURE,
            summary="Cloud model tests require online runtime",
            input_payload=normalized_inputs,
            output_payload={},
            error_details={"error": "offline_not_allowed", "runtime_profile": runtime_profile},
            latency_ms=None,
            config_fingerprint=config_fingerprint,
            tested_by_user_id=actor_user_id,
        )
        raise ModelOpsError(
            "offline_not_allowed",
            "Model test is not available in offline mode",
            status_code=409,
            details={"test_run": serialize_model_test_run(test_run)},
        )

    if backend_kind != "external_api":
        test_run = modelops_repo.append_model_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            result=modelops_repo.TEST_FAILURE,
            summary="Local model testing is not available in the current platform runtime",
            input_payload=normalized_inputs,
            output_payload={},
            error_details={"error": "local_prevalidation_execution_unavailable"},
            latency_ms=None,
            config_fingerprint=config_fingerprint,
            tested_by_user_id=actor_user_id,
        )
        raise ModelOpsError(
            "model_test_not_supported",
            "Testing unavailable for this local model in the current platform runtime",
            status_code=409,
            details={"test_run": serialize_model_test_run(test_run)},
        )

    secret = _credential_secret_for_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        row=row,
    )

    try:
        if task_key == modelops_repo.TASK_LLM:
            summary, request_payload, output_payload, result_payload, latency_ms = _execute_cloud_llm_test(
                row,
                secret=secret,
                prompt=normalized_inputs["prompt"],
            )
        elif task_key == modelops_repo.TASK_EMBEDDINGS:
            summary, request_payload, output_payload, result_payload, latency_ms = _execute_cloud_embeddings_test(
                row,
                secret=secret,
                text=normalized_inputs["text"],
            )
        else:
            raise ModelOpsError("model_test_unsupported", "Testing is not supported for this model type", status_code=409)
        test_run = modelops_repo.append_model_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            result=modelops_repo.TEST_SUCCESS,
            summary=summary,
            input_payload=request_payload,
            output_payload=output_payload,
            error_details={},
            latency_ms=latency_ms,
            config_fingerprint=config_fingerprint,
            tested_by_user_id=actor_user_id,
        )
    except ModelOpsError as exc:
        error_details = exc.details.get("error_details") if isinstance(exc.details, dict) else {}
        output_payload = exc.details.get("output_payload") if isinstance(exc.details, dict) else {}
        latency_ms = exc.details.get("latency_ms") if isinstance(exc.details, dict) else None
        summary = str(exc.details.get("summary") or exc.message) if isinstance(exc.details, dict) else exc.message
        test_run = modelops_repo.append_model_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            result=modelops_repo.TEST_FAILURE,
            summary=summary,
            input_payload=normalized_inputs,
            output_payload=output_payload if isinstance(output_payload, dict) else {},
            error_details=error_details if isinstance(error_details, dict) else {"message": exc.message},
            latency_ms=float(latency_ms) if isinstance(latency_ms, (float, int)) else None,
            config_fingerprint=config_fingerprint,
            tested_by_user_id=actor_user_id,
        )
        raise ModelOpsError(
            exc.code,
            exc.message,
            status_code=exc.status_code,
            details={"test_run": serialize_model_test_run(test_run)},
        ) from exc

    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.tested",
        target_type="model",
        target_id=model_id,
        payload={"task_key": task_key, "test_run_id": str(test_run.get("id")), "result": test_run.get("result")},
    )
    return {
        "model": serialize_model(modelops_repo.get_model(database_url, model_id) or row),
        "test_run": serialize_model_test_run(test_run),
        "result": result_payload,
    }


def validate_model(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    trigger_reason: str = "manual_after_test",
    test_run_id: str | None = None,
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
    if not test_run_id:
        raise ModelOpsError("validation_test_required", "Validation requires a successful model test run", status_code=400)

    test_run = modelops_repo.get_model_test_run(database_url, test_run_id)
    if test_run is None:
        raise ModelOpsError("test_run_not_found", "Model test run not found", status_code=404)
    if str(test_run.get("model_id", "")).strip() != model_id.strip():
        raise ModelOpsError("test_run_mismatch", "Model test run does not belong to this model", status_code=409)
    if str(test_run.get("result", "")).strip().lower() != modelops_repo.TEST_SUCCESS:
        raise ModelOpsError("validation_test_failed", "Only successful model tests can be validated", status_code=409)

    config_fingerprint = str(row.get("current_config_fingerprint") or modelops_repo.compute_config_fingerprint(row))
    if str(test_run.get("config_fingerprint", "")).strip() != config_fingerprint:
        raise ModelOpsError("validation_test_stale", "Model configuration changed after the successful test run", status_code=409)

    validation = modelops_repo.append_validation(
        database_url,
        model_id=model_id,
        validator_kind=f"{str(row.get('task_key', '')).strip().lower() or 'model'}_test_confirmation",
        trigger_reason=trigger_reason,
        result=modelops_repo.VALIDATION_SUCCESS,
        summary="Model validation confirmed from successful test run",
        error_details={"test_run_id": str(test_run.get("id"))},
        config_fingerprint=config_fingerprint,
        validated_by_user_id=actor_user_id,
    )

    modelops_repo.append_audit_event(
        database_url,
        actor_user_id=actor_user_id,
        event_type="model.validated",
        target_type="model",
        target_id=model_id,
        payload={"validator_kind": validation.get("validator_kind"), "result": validation.get("result"), "test_run_id": str(test_run.get("id"))},
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
