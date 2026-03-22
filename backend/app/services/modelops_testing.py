from __future__ import annotations

from time import perf_counter
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import get_active_credential_secret_by_id
from .modelops_common import ModelOpsError
from .modelops_policy import can_manage_model, get_accessible_model
from .modelops_serializers import serialize_model, serialize_model_test_run
from .platform_adapters import http_json_request
from .runtime_profile_service import resolve_runtime_profile


def get_model_tests(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    from .modelops_queries import get_model_tests as get_model_tests_query

    return get_model_tests_query(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        limit=limit,
    )


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


def _credential_secret_for_model_test(
    database_url: str,
    *,
    config: AuthConfig,
    row: dict[str, Any],
) -> dict[str, Any]:
    credential_id = str(row.get("credential_id", "")).strip()
    if not credential_id:
        raise ModelOpsError("missing_config", "Cloud model is missing a credential", status_code=400)
    secret = get_active_credential_secret_by_id(
        database_url,
        credential_id=credential_id,
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
        headers={"Authorization": f"Bearer {str(secret.get('api_key') or '').strip()}"},
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
        "metadata": {"model": provider_model_id, "status_code": status_code},
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

    request_payload = {"model": provider_model_id, "input": [text]}
    started_at = perf_counter()
    payload, status_code = http_json_request(
        f"{api_base_url}/embeddings",
        method="POST",
        payload=request_payload,
        headers={"Authorization": f"Bearer {str(secret.get('api_key') or '').strip()}"},
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
        "metadata": {"model": provider_model_id, "count": len(vectors), "status_code": status_code},
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
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")

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

    secret = _credential_secret_for_model_test(
        database_url,
        config=config,
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
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")
    lifecycle_state = str(row.get("lifecycle_state", "")).strip().lower() or modelops_repo.LIFECYCLE_REGISTERED
    if lifecycle_state not in {
        modelops_repo.LIFECYCLE_REGISTERED,
        modelops_repo.LIFECYCLE_INACTIVE,
        modelops_repo.LIFECYCLE_VALIDATED,
        modelops_repo.LIFECYCLE_ACTIVE,
    }:
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
        payload={
            "validator_kind": validation.get("validator_kind"),
            "result": validation.get("result"),
            "test_run_id": str(test_run.get("id")),
        },
    )
    return {
        "model": serialize_model(modelops_repo.get_model(database_url, model_id) or row),
        "validation": validation,
    }
