from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flask import g

from ..config import get_auth_config
from ..repositories import modelops as modelops_repo
from .modelops_common import ModelOpsError
from .modelops_runtime import ensure_model_invokable, measure_and_record_inference
from .platform_service import resolve_llm_inference_adapter
from .platform_types import PlatformControlPlaneError


def coerce_chat_messages(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        if not content:
            continue
        normalized.append(
            {
                "role": role,
                "content": [{"type": "text", "text": content}],
            }
        )
    return normalized


def extract_output_text(llm_response: dict[str, Any]) -> str:
    output = llm_response.get("output")
    if not isinstance(output, list) or len(output) == 0:
        return ""

    first = output[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, list) or len(content) == 0:
        return ""

    text_parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and str(part.get("type", "")).lower() == "text":
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def _can_use_local_llm_fallback(model: dict[str, Any] | None) -> bool:
    if model is None:
        return False
    backend_kind = str(model.get("backend_kind", "")).strip().lower()
    availability = str(model.get("availability", "")).strip().lower()
    return backend_kind == "local" or availability == "offline_ready"


def _resolve_canonical_local_llm_model_id(adapter: Any, model_row: dict[str, Any]) -> str:
    requested_model_id = str(model_row.get("id") or model_row.get("model_id") or "").strip()
    if not _can_use_local_llm_fallback(model_row):
        return requested_model_id

    binding = getattr(adapter, "binding", None)
    config = getattr(binding, "config", None)
    if not isinstance(config, dict):
        return requested_model_id

    canonical_local_model_id = str(config.get("canonical_local_model_id", "")).strip()
    if canonical_local_model_id:
        return canonical_local_model_id

    fallback_model_id = str(config.get("local_fallback_model_id", "")).strip()
    if fallback_model_id:
        return fallback_model_id

    return requested_model_id


def _select_bound_llm_model(adapter: Any, requested_model_id: str) -> dict[str, Any]:
    binding = getattr(adapter, "binding", None)
    served_models = getattr(binding, "served_models", None)
    if not isinstance(served_models, list) or not served_models:
        raise PlatformControlPlaneError(
            "served_model_required",
            "Active LLM binding is missing served models",
            status_code=503,
            details={"provider": getattr(binding, "provider_slug", None)},
        )
    for served_model in served_models:
        if not isinstance(served_model, dict):
            continue
        if str(served_model.get("id", "")).strip() == requested_model_id:
            return dict(served_model)
    raise PlatformControlPlaneError(
        "model_not_bound",
        "Requested model is not served by the active LLM deployment binding",
        status_code=409,
        details={"model_id": requested_model_id, "provider": getattr(binding, "provider_slug", None)},
    )


def _resolve_runtime_model_id(adapter: Any, served_model: dict[str, Any]) -> str:
    provider_model_id = str(served_model.get("provider_model_id", "")).strip()
    if provider_model_id:
        return provider_model_id

    list_models = getattr(adapter, "list_models", None)
    if not callable(list_models):
        raise PlatformControlPlaneError(
            "provider_inventory_unavailable",
            "LLM provider cannot resolve served model identifiers",
            status_code=502,
            details={"served_model_id": served_model.get("id")},
        )
    models_payload, status_code = list_models()
    if models_payload is None or not 200 <= status_code < 300:
        raise PlatformControlPlaneError(
            "provider_inventory_unavailable",
            "Unable to query the active LLM provider model inventory",
            status_code=502 if status_code < 500 else status_code,
            details={"served_model_id": served_model.get("id"), "status_code": status_code},
        )
    candidates = [
        str(served_model.get("local_path", "")).strip(),
        str(served_model.get("id", "")).strip(),
        str(served_model.get("name", "")).strip(),
        str(served_model.get("source_id", "")).strip(),
    ]
    available_ids = {
        str(item.get("id", "")).strip()
        for item in (models_payload.get("data") if isinstance(models_payload.get("data"), list) else [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    for candidate in candidates:
        if candidate and candidate in available_ids:
            return candidate

    raw_model_id = str(served_model.get("id", "")).strip()
    raw_model_row = modelops_repo.get_model(get_auth_config().database_url, raw_model_id)
    if raw_model_row is not None:
        fallback_model_id = _resolve_canonical_local_llm_model_id(adapter, raw_model_row)
        if fallback_model_id and fallback_model_id in available_ids:
            return fallback_model_id

    raise PlatformControlPlaneError(
        "model_not_exposed_by_provider",
        "Requested model is not exposed by the active LLM provider",
        status_code=409,
        details={"served_model_id": served_model.get("id"), "available_models": sorted(available_ids)},
    )


def _resolve_chat_completion_target(
    *,
    requested_model_id: str,
) -> tuple[Any | None, str, bool, dict[str, Any] | None, int]:
    try:
        model_row = ensure_model_invokable(
            get_auth_config().database_url,
            config=get_auth_config(),
            user_id=int(g.current_user["id"]),
            user_role=str(getattr(g, "current_user", {}) and g.current_user.get("role", "user")),
            model_id=requested_model_id,
        )
    except ModelOpsError as exc:
        return None, requested_model_id, False, {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code

    try:
        adapter = resolve_llm_inference_adapter(get_auth_config().database_url, get_auth_config())
    except PlatformControlPlaneError as exc:
        return None, requested_model_id, False, {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code

    raw_model_row = modelops_repo.get_model(get_auth_config().database_url, requested_model_id) or model_row
    allow_local_fallback = _can_use_local_llm_fallback(raw_model_row)
    try:
        served_model = _select_bound_llm_model(adapter, requested_model_id)
        llm_model_id = _resolve_runtime_model_id(adapter, served_model)
    except PlatformControlPlaneError as exc:
        return None, requested_model_id, False, {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code
    return adapter, llm_model_id, allow_local_fallback, None, 200


def chat_completion_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[dict[str, Any] | None, int]:
    _ = org_id
    _ = group_id
    adapter, llm_model_id, allow_local_fallback, error_payload, status_code = _resolve_chat_completion_target(
        requested_model_id=requested_model_id,
    )
    if error_payload is not None:
        return error_payload, status_code

    return measure_and_record_inference(
        get_auth_config().database_url,
        model_id=requested_model_id,
        user_id=int(g.current_user["id"]) if getattr(g, "current_user", None) else None,
        callable_fn=lambda: adapter.chat_completion(
            model=llm_model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            allow_local_fallback=allow_local_fallback,
        ),
    )


def chat_completion_stream_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[Iterator[dict[str, Any]] | None, dict[str, Any] | None, int]:
    _ = org_id
    _ = group_id
    adapter, llm_model_id, allow_local_fallback, error_payload, status_code = _resolve_chat_completion_target(
        requested_model_id=requested_model_id,
    )
    if error_payload is not None:
        return None, error_payload, status_code

    return (
        adapter.chat_completion_stream(
            model=llm_model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            allow_local_fallback=allow_local_fallback,
        ),
        None,
        200,
    )
