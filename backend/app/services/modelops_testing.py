from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories import platform_control_plane as platform_repo
from ..repositories.model_credentials import get_active_credential_secret_by_id
from .modelops_common import ModelOpsError
from .modelops_policy import can_manage_model, get_accessible_model
from .modelops_serializers import serialize_model, serialize_model_test_run
from .platform_adapters import build_credential_openai_compatible_llm_adapter, http_json_request
from .platform_service import (
    _effective_local_slot,
    ensure_platform_bootstrap_state,
    resolve_embeddings_adapter,
    resolve_llm_inference_adapter,
)
from .runtime_profile_service import resolve_runtime_profile

_TASK_LLM = modelops_repo.TASK_LLM
_TASK_EMBEDDINGS = modelops_repo.TASK_EMBEDDINGS
_CLOUD_PROVIDER_KEYS = {"openai_compatible_cloud_llm", "openai_compatible_cloud_embeddings"}
_LOCAL_TEST_CAPABILITY_BY_TASK = {
    _TASK_LLM: "llm_inference",
    _TASK_EMBEDDINGS: "embeddings",
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
    output = payload.get("output")
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, dict):
            content = first.get("content")
            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and str(item.get("type", "")).strip().lower() == "text":
                        text = str(item.get("text", "")).strip()
                        if text:
                            text_parts.append(text)
                if text_parts:
                    return "\n".join(text_parts)

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

    adapter = build_credential_openai_compatible_llm_adapter(
        api_base_url=api_base_url,
        api_key=str(secret.get("api_key") or "").strip(),
        provider_slug=str(secret.get("provider_slug") or row.get("provider") or "openai_compatible").strip(),
        timeout_seconds=8.0,
    )
    messages = [{"role": "user", "content": prompt}]
    request_payload = adapter.build_chat_completion_payload(
        model=provider_model_id,
        max_tokens=64,
        messages=messages,
        temperature=0,
    )
    started_at = perf_counter()
    payload, status_code = adapter.chat_completion(
        model=provider_model_id,
        messages=messages,
        max_tokens=64,
        temperature=0,
        allow_local_fallback=False,
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


def _normalized_identifier_candidates(value: Any) -> set[str]:
    raw_value = str(value or "").strip()
    if not raw_value:
        return set()

    candidates = {raw_value.lower()}
    if any(raw_value.startswith(prefix) for prefix in ("/", ".", "~")) or "/" in raw_value:
        try:
            candidates.add(str(Path(raw_value).expanduser().resolve(strict=False)).lower())
        except OSError:
            pass
    return candidates


def _managed_model_identifiers(row: dict[str, Any]) -> list[tuple[str, str]]:
    artifact = row.get("artifact") if isinstance(row.get("artifact"), dict) else {}
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    identifiers = [
        ("model_id", str(row.get("model_id") or "").strip()),
        ("source_id", str(row.get("source_id") or "").strip()),
        ("provider_model_id", str(row.get("provider_model_id") or "").strip()),
        ("local_path", str(row.get("local_path") or "").strip()),
        ("artifact.storage_path", str(artifact.get("storage_path") or "").strip()),
        ("metadata.source_id", str(metadata.get("source_id") or "").strip()),
        ("metadata.local_path", str(metadata.get("local_path") or "").strip()),
        ("metadata.upstream_model", str(metadata.get("upstream_model") or "").strip()),
    ]
    return [(label, value) for label, value in identifiers if value]


def _runtime_entry_identifiers(entry: dict[str, Any]) -> list[tuple[str, str]]:
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    identifiers = [
        ("id", str(entry.get("id") or "").strip()),
        ("source_id", str(entry.get("source_id") or "").strip()),
        ("provider_model_id", str(entry.get("provider_model_id") or "").strip()),
        ("local_path", str(entry.get("local_path") or "").strip()),
        ("upstream_model", str(entry.get("upstream_model") or "").strip()),
        ("metadata.source_id", str(metadata.get("source_id") or "").strip()),
        ("metadata.local_path", str(metadata.get("local_path") or "").strip()),
        ("metadata.upstream_model", str(metadata.get("upstream_model") or "").strip()),
    ]
    return [(label, value) for label, value in identifiers if value]


def _runtime_advertised_model_ids(runtime_models: list[dict[str, Any]]) -> list[str]:
    advertised: list[str] = []
    seen: set[str] = set()
    for runtime_entry in runtime_models:
        normalized = str(runtime_entry.get("id") or "").strip()
        lowered = normalized.lower()
        if normalized and lowered not in seen:
            advertised.append(normalized)
            seen.add(lowered)
    return advertised


def _serialize_runtime_inventory_entry(runtime_entry: dict[str, Any]) -> dict[str, Any]:
    capabilities = runtime_entry.get("capabilities") if isinstance(runtime_entry.get("capabilities"), dict) else {}
    metadata = runtime_entry.get("metadata") if isinstance(runtime_entry.get("metadata"), dict) else {}
    return {
        "id": str(runtime_entry.get("id") or "").strip(),
        "display_name": str(runtime_entry.get("display_name") or runtime_entry.get("id") or "").strip(),
        "capabilities": {
            "text": bool(capabilities.get("text")),
            "image_input": bool(capabilities.get("image_input")),
            "embeddings": bool(capabilities.get("embeddings")),
        },
        "metadata": dict(metadata),
    }


def _find_runtime_model_match(model_row: dict[str, Any], runtime_models: list[dict[str, Any]]) -> dict[str, str] | None:
    managed_identifiers = _managed_model_identifiers(model_row)
    for runtime_entry in runtime_models:
        runtime_identifiers = _runtime_entry_identifiers(runtime_entry)
        for managed_source, managed_value in managed_identifiers:
            managed_candidates = _normalized_identifier_candidates(managed_value)
            if not managed_candidates:
                continue
            for runtime_source, runtime_value in runtime_identifiers:
                runtime_candidates = _normalized_identifier_candidates(runtime_value)
                if runtime_candidates and managed_candidates.intersection(runtime_candidates):
                    return {
                        "runtime_model_id": str(runtime_entry.get("id") or "").strip(),
                        "runtime_model_display_name": str(runtime_entry.get("display_name") or runtime_entry.get("id") or "").strip(),
                        "managed_source": managed_source,
                        "runtime_source": runtime_source,
                        "matched_value": runtime_value,
                    }
    return None


def _local_test_capability_for_task(task_key: str) -> str | None:
    return _LOCAL_TEST_CAPABILITY_BY_TASK.get(task_key.strip().lower())


def _list_local_test_provider_rows(
    database_url: str,
    *,
    config: AuthConfig,
    task_key: str,
) -> tuple[list[dict[str, Any]], str | None]:
    capability_key = _local_test_capability_for_task(task_key)
    if capability_key is None:
        return [], None
    ensure_platform_bootstrap_state(database_url, config)
    provider_rows = [
        row
        for row in platform_repo.list_provider_instances(database_url)
        if str(row.get("capability_key", "")).strip().lower() == capability_key
        and bool(row.get("enabled"))
        and str(row.get("provider_key", "")).strip().lower() not in _CLOUD_PROVIDER_KEYS
    ]
    active_binding = platform_repo.get_active_binding_for_capability(database_url, capability_key=capability_key)
    active_provider_instance_id = (
        str(active_binding.get("provider_instance_id") or "").strip() if isinstance(active_binding, dict) else None
    ) or None
    return provider_rows, active_provider_instance_id


def _inspect_local_llm_test_runtime(
    database_url: str,
    *,
    config: AuthConfig,
    model_row: dict[str, Any],
    provider_row: dict[str, Any],
    is_active: bool,
) -> dict[str, Any]:
    provider_instance_id = str(provider_row.get("id") or "").strip()
    capability_key = str(provider_row.get("capability_key") or "").strip().lower()
    local_slot = _effective_local_slot(provider_row)
    loaded_managed_model_id = str(local_slot.get("loaded_managed_model_id") or "").strip() or None
    loaded_managed_model_name = str(local_slot.get("loaded_managed_model_name") or "").strip() or None
    loaded_runtime_model_id = str(local_slot.get("loaded_runtime_model_id") or "").strip() or None
    loaded_local_path = str(local_slot.get("loaded_local_path") or "").strip() or None
    loaded_source_id = str(local_slot.get("loaded_source_id") or "").strip() or None
    load_state = str(local_slot.get("load_state") or "").strip().lower() or ("reconciling" if loaded_managed_model_id else "empty")
    load_error = str(local_slot.get("load_error") or "").strip() or None
    if capability_key == "llm_inference":
        adapter = resolve_llm_inference_adapter(
            database_url,
            config,
            provider_instance_id=provider_instance_id,
        )
    elif capability_key == "embeddings":
        adapter = resolve_embeddings_adapter(
            database_url,
            config,
            provider_instance_id=provider_instance_id,
        )
    else:
        raise ModelOpsError("test_runtime_not_supported", "Provider does not support local model testing", status_code=409)
    models_payload, status_code = adapter.list_models()
    runtime_models = models_payload.get("data") if isinstance(models_payload, dict) else None
    available_models = [item for item in runtime_models if isinstance(item, dict)] if isinstance(runtime_models, list) else []
    reachable = models_payload is not None and 200 <= status_code < 300
    match = _find_runtime_model_match(model_row, available_models) if reachable else None
    advertised_model_ids = _runtime_advertised_model_ids(available_models) if reachable else []
    advertised_models = [_serialize_runtime_inventory_entry(item) for item in available_models]
    if loaded_runtime_model_id:
        available_runtime_ids = {
            str(item.get("id") or "").strip()
            for item in available_models
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        if loaded_runtime_model_id in available_runtime_ids:
            load_state = "loaded"
            load_error = None
        elif load_state == "loading":
            pass
        elif reachable:
            load_state = "reconciling"
        else:
            load_state = "error"
            if not load_error:
                load_error = f"runtime_inventory_unavailable:{status_code}"
    message = (
        "Runtime serves the selected local model"
        if match
        else "Runtime does not currently serve the selected local model"
        if reachable
        else "Runtime is unavailable"
    )
    return {
        "provider_instance_id": provider_instance_id,
        "slug": str(provider_row.get("slug") or "").strip(),
        "display_name": str(provider_row.get("display_name") or provider_row.get("slug") or "").strip(),
        "provider_key": str(provider_row.get("provider_key") or "").strip(),
        "endpoint_url": str(provider_row.get("endpoint_url") or "").strip(),
        "adapter_kind": str(provider_row.get("adapter_kind") or "").strip(),
        "enabled": bool(provider_row.get("enabled")),
        "is_active": is_active,
        "reachable": reachable,
        "status_code": status_code,
        "matches_model": match is not None,
        "matched_model_id": match["runtime_model_id"] if match is not None else None,
        "matched_model_display_name": match["runtime_model_display_name"] if match is not None else None,
        "match_source": (
            f"{match['managed_source']} -> {match['runtime_source']}"
            if match is not None
            else None
        ),
        "matched_value": match["matched_value"] if match is not None else None,
        "loaded_managed_model_id": loaded_managed_model_id,
        "loaded_managed_model_name": loaded_managed_model_name,
        "loaded_runtime_model_id": loaded_runtime_model_id,
        "loaded_local_path": loaded_local_path,
        "loaded_source_id": loaded_source_id,
        "load_state": load_state,
        "load_error": load_error,
        "advertised_model_ids": advertised_model_ids,
        "advertised_models": advertised_models,
        "message": message,
    }


def get_model_test_runtimes(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")

    backend_kind = str(row.get("backend_kind", "")).strip().lower()
    task_key = str(row.get("task_key", "")).strip().lower() or _TASK_LLM
    if backend_kind != "local" or _local_test_capability_for_task(task_key) is None:
        return {
            "model_id": model_id,
            "runtimes": [],
            "default_provider_instance_id": None,
        }

    provider_rows, active_provider_instance_id = _list_local_test_provider_rows(
        database_url,
        config=config,
        task_key=task_key,
    )
    runtimes = [
        _inspect_local_llm_test_runtime(
            database_url,
            config=config,
            model_row=row,
            provider_row=provider_row,
            is_active=str(provider_row.get("id") or "").strip() == active_provider_instance_id,
        )
        for provider_row in provider_rows
    ]

    default_runtime = next((item for item in runtimes if item["is_active"] and item["matches_model"]), None)
    if default_runtime is None:
        default_runtime = next((item for item in runtimes if item["matches_model"]), None)

    return {
        "model_id": model_id,
        "runtimes": runtimes,
        "default_provider_instance_id": (
            str(default_runtime.get("provider_instance_id") or "").strip() if isinstance(default_runtime, dict) else None
        )
        or None,
    }


def _append_failed_test_run(
    database_url: str,
    *,
    model_id: str,
    task_key: str,
    normalized_inputs: dict[str, str],
    config_fingerprint: str,
    actor_user_id: int,
    summary: str,
    error_details: dict[str, Any],
    latency_ms: float | None = None,
) -> dict[str, Any]:
    return modelops_repo.append_model_test_run(
        database_url,
        model_id=model_id,
        task_key=task_key,
        result=modelops_repo.TEST_FAILURE,
        summary=summary,
        input_payload=normalized_inputs,
        output_payload={},
        error_details=error_details,
        latency_ms=latency_ms,
        config_fingerprint=config_fingerprint,
        tested_by_user_id=actor_user_id,
    )


def _resolve_superadmin_local_test_runtime(
    database_url: str,
    *,
    config: AuthConfig,
    row: dict[str, Any],
    provider_instance_id: str | None,
) -> dict[str, Any]:
    runtime_payload = get_model_test_runtimes(
        database_url,
        config=config,
        actor_user_id=0,
        actor_role="superadmin",
        model_id=str(row.get("model_id") or ""),
    )
    runtimes = runtime_payload.get("runtimes") if isinstance(runtime_payload, dict) else []
    runtime_options = [item for item in runtimes if isinstance(item, dict)]
    if provider_instance_id:
        selected = next(
            (item for item in runtime_options if str(item.get("provider_instance_id") or "").strip() == provider_instance_id),
            None,
        )
    else:
        default_provider_instance_id = str(runtime_payload.get("default_provider_instance_id") or "").strip()
        selected = next(
            (
                item
                for item in runtime_options
                if str(item.get("provider_instance_id") or "").strip() == default_provider_instance_id
            ),
            None,
        )
    return {
        "selected_runtime": selected,
        "runtime_options": runtime_options,
        "default_provider_instance_id": str(runtime_payload.get("default_provider_instance_id") or "").strip() or None,
    }


def _execute_local_llm_test(
    database_url: str,
    *,
    config: AuthConfig,
    row: dict[str, Any],
    prompt: str,
    provider_instance_id: str,
    runtime_model_id: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], float]:
    adapter = resolve_llm_inference_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )
    request_payload = {
        "provider_instance_id": provider_instance_id,
        "model": runtime_model_id,
        "input": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "allow_local_fallback": False,
    }
    started_at = perf_counter()
    payload, status_code = adapter.chat_completion(
        model=runtime_model_id,
        messages=request_payload["input"],
        max_tokens=64,
        temperature=0,
        allow_local_fallback=False,
    )
    latency_ms = (perf_counter() - started_at) * 1000
    response_payload = payload if isinstance(payload, dict) else {}
    if payload is None or status_code >= 400:
        message = str(response_payload.get("message") or response_payload.get("error") or "Local LLM test failed")
        raise ModelOpsError(
            "model_test_failed",
            message,
            status_code=409,
            details={
                "summary": "Local LLM test failed",
                "output_payload": response_payload,
                "error_details": {
                    "status_code": status_code,
                    "message": message,
                    "provider_instance_id": provider_instance_id,
                    "runtime_model_id": runtime_model_id,
                },
                "latency_ms": latency_ms,
            },
        )
    response_text = _extract_llm_response_text(response_payload)
    result_payload = {
        "kind": _TASK_LLM,
        "success": True,
        "response_text": response_text,
        "latency_ms": latency_ms,
        "metadata": {
            "provider_instance_id": provider_instance_id,
            "runtime_model_id": runtime_model_id,
            "managed_model_id": str(row.get("model_id") or "").strip(),
            "status_code": status_code,
        },
    }
    return "Local LLM test succeeded", request_payload, response_payload, result_payload, latency_ms


def _execute_local_embeddings_test(
    database_url: str,
    *,
    config: AuthConfig,
    row: dict[str, Any],
    text: str,
    provider_instance_id: str,
    runtime_model_id: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], float]:
    adapter = resolve_embeddings_adapter(
        database_url,
        config,
        provider_instance_id=provider_instance_id,
    )
    request_payload = {
        "provider_instance_id": provider_instance_id,
        "model": runtime_model_id,
        "input": [text],
    }
    started_at = perf_counter()
    payload, status_code = adapter.embed_texts(texts=[text], model=runtime_model_id)
    latency_ms = (perf_counter() - started_at) * 1000
    response_payload = payload if isinstance(payload, dict) else {}
    if payload is None or status_code >= 400:
        message = str(response_payload.get("message") or response_payload.get("error") or "Local embeddings test failed")
        raise ModelOpsError(
            "model_test_failed",
            message,
            status_code=409,
            details={
                "summary": "Local embeddings test failed",
                "output_payload": response_payload,
                "error_details": {
                    "status_code": status_code,
                    "message": message,
                    "provider_instance_id": provider_instance_id,
                    "runtime_model_id": runtime_model_id,
                },
                "latency_ms": latency_ms,
            },
        )

    embeddings = response_payload.get("embeddings")
    vectors = embeddings if isinstance(embeddings, list) else []
    first_vector = vectors[0] if vectors else []
    dimension = len(first_vector) if isinstance(first_vector, list) else 0
    result_payload = {
        "kind": _TASK_EMBEDDINGS,
        "success": True,
        "dimension": dimension,
        "latency_ms": latency_ms,
        "vector_preview": first_vector[:8] if isinstance(first_vector, list) else [],
        "metadata": {
            "provider_instance_id": provider_instance_id,
            "runtime_model_id": runtime_model_id,
            "managed_model_id": str(row.get("model_id") or "").strip(),
            "status_code": status_code,
        },
    }
    return "Local embeddings test succeeded", request_payload, response_payload, result_payload, latency_ms


def run_model_test(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    inputs: dict[str, Any],
    provider_instance_id: str | None = None,
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
        test_run = _append_failed_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            summary="Cloud model tests require online runtime",
            error_details={"error": "offline_not_allowed", "runtime_profile": runtime_profile},
            config_fingerprint=config_fingerprint,
            normalized_inputs=normalized_inputs,
            actor_user_id=actor_user_id,
        )
        raise ModelOpsError(
            "offline_not_allowed",
            "Model test is not available in offline mode",
            status_code=409,
            details={"test_run": serialize_model_test_run(test_run)},
        )

    if backend_kind == "local" and task_key in {_TASK_LLM, _TASK_EMBEDDINGS}:
        normalized_provider_instance_id = str(provider_instance_id or "").strip() or None
        if actor_role.strip().lower() != "superadmin":
            test_run = _append_failed_test_run(
                database_url,
                model_id=model_id,
                task_key=task_key,
                summary="Local model tests require superadmin runtime selection",
                error_details={"error": "local_model_runtime_selection_required"},
                config_fingerprint=config_fingerprint,
                normalized_inputs=normalized_inputs,
                actor_user_id=actor_user_id,
            )
            raise ModelOpsError(
                "local_model_runtime_selection_required",
                "Local model testing requires a superadmin to choose a compatible runtime",
                status_code=409,
                details={"test_run": serialize_model_test_run(test_run)},
            )

        runtime_resolution = _resolve_superadmin_local_test_runtime(
            database_url,
            config=config,
            row=row,
            provider_instance_id=normalized_provider_instance_id,
        )
        selected_runtime = runtime_resolution["selected_runtime"]
        runtime_options = runtime_resolution["runtime_options"]
        default_provider_instance_id = runtime_resolution["default_provider_instance_id"]

        if normalized_provider_instance_id and selected_runtime is None:
            test_run = _append_failed_test_run(
                database_url,
                model_id=model_id,
                task_key=task_key,
                summary="Selected local test runtime was not found",
                error_details={
                    "error": "test_runtime_not_found",
                    "provider_instance_id": normalized_provider_instance_id,
                },
                config_fingerprint=config_fingerprint,
                normalized_inputs=normalized_inputs,
                actor_user_id=actor_user_id,
            )
            raise ModelOpsError(
                "test_runtime_not_found",
                "Selected test runtime was not found",
                status_code=404,
                details={"test_run": serialize_model_test_run(test_run)},
            )

        if selected_runtime is None:
            test_run = _append_failed_test_run(
                database_url,
                model_id=model_id,
                task_key=task_key,
                summary="No compatible local runtime currently serves this model",
                error_details={
                    "error": "local_model_not_served_by_runtime",
                    "runtime_count": len(runtime_options),
                    "default_provider_instance_id": default_provider_instance_id,
                },
                config_fingerprint=config_fingerprint,
                normalized_inputs=normalized_inputs,
                actor_user_id=actor_user_id,
            )
            raise ModelOpsError(
                "local_model_not_served_by_runtime",
                "No compatible runtime currently serves this local model",
                status_code=409,
                details={"test_run": serialize_model_test_run(test_run)},
            )

        if not bool(selected_runtime.get("reachable")):
            test_run = _append_failed_test_run(
                database_url,
                model_id=model_id,
                task_key=task_key,
                summary="Selected local test runtime is unavailable",
                error_details={
                    "error": "test_runtime_unreachable",
                    "provider_instance_id": selected_runtime.get("provider_instance_id"),
                    "status_code": selected_runtime.get("status_code"),
                },
                config_fingerprint=config_fingerprint,
                normalized_inputs=normalized_inputs,
                actor_user_id=actor_user_id,
            )
            raise ModelOpsError(
                "test_runtime_unreachable",
                "Selected runtime is unavailable for local model testing",
                status_code=502,
                details={"test_run": serialize_model_test_run(test_run)},
            )

        if not bool(selected_runtime.get("matches_model")):
            test_run = _append_failed_test_run(
                database_url,
                model_id=model_id,
                task_key=task_key,
                summary="Selected runtime does not serve this local model",
                error_details={
                    "error": "local_model_not_served_by_runtime",
                    "provider_instance_id": selected_runtime.get("provider_instance_id"),
                },
                config_fingerprint=config_fingerprint,
                normalized_inputs=normalized_inputs,
                actor_user_id=actor_user_id,
            )
            raise ModelOpsError(
                "local_model_not_served_by_runtime",
                "Selected runtime does not serve this local model",
                status_code=409,
                details={"test_run": serialize_model_test_run(test_run)},
            )

        try:
            if task_key == _TASK_LLM:
                summary, request_payload, output_payload, result_payload, latency_ms = _execute_local_llm_test(
                    database_url,
                    config=config,
                    row=row,
                    prompt=normalized_inputs["prompt"],
                    provider_instance_id=str(selected_runtime.get("provider_instance_id") or "").strip(),
                    runtime_model_id=str(selected_runtime.get("matched_model_id") or "").strip(),
                )
            else:
                summary, request_payload, output_payload, result_payload, latency_ms = _execute_local_embeddings_test(
                    database_url,
                    config=config,
                    row=row,
                    text=normalized_inputs["text"],
                    provider_instance_id=str(selected_runtime.get("provider_instance_id") or "").strip(),
                    runtime_model_id=str(selected_runtime.get("matched_model_id") or "").strip(),
                )
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

    if backend_kind != "external_api":
        test_run = _append_failed_test_run(
            database_url,
            model_id=model_id,
            task_key=task_key,
            summary="Testing is not supported for this model runtime combination",
            error_details={"error": "model_test_not_supported"},
            config_fingerprint=config_fingerprint,
            normalized_inputs=normalized_inputs,
            actor_user_id=actor_user_id,
        )
        raise ModelOpsError(
            "model_test_not_supported",
            "Testing unavailable for this model in the current configuration",
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
    if bool(row.get("is_validation_current")) and str(row.get("last_validation_status", "")).strip().lower() == modelops_repo.VALIDATION_SUCCESS:
        raise ModelOpsError(
            "validation_already_current",
            "Model is already validated for its current configuration",
            status_code=409,
        )
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
