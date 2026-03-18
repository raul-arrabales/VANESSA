from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flask import g

from ..config import get_auth_config
from ..repositories.model_management import get_model_by_id
from .model_resolution import resolve_model_for_inference
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


def _can_use_local_llm_fallback(requested_model_id: str) -> bool:
    model = get_model_by_id(get_auth_config().database_url, requested_model_id)
    if model is None:
        return False
    backend_kind = str(model.get("backend_kind", "")).strip().lower()
    availability = str(model.get("availability", "")).strip().lower()
    return backend_kind == "local" or availability == "offline_ready"


def _resolve_canonical_local_llm_model_id(adapter: Any, requested_model_id: str) -> str:
    if not _can_use_local_llm_fallback(requested_model_id):
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


def _resolve_chat_completion_target(
    *,
    requested_model_id: str,
) -> tuple[Any | None, str, bool, dict[str, Any] | None, int]:
    resolved_model_id, error_payload, status_code = resolve_model_for_inference(
        get_auth_config().database_url,
        user_id=int(g.current_user["id"]),
        requested_model_id=requested_model_id,
    )
    if error_payload is not None:
        return None, requested_model_id, False, error_payload, status_code

    try:
        adapter = resolve_llm_inference_adapter(get_auth_config().database_url, get_auth_config())
    except PlatformControlPlaneError as exc:
        return None, requested_model_id, False, {
            "error": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        }, exc.status_code

    effective_requested_model = str(resolved_model_id or requested_model_id)
    allow_local_fallback = _can_use_local_llm_fallback(effective_requested_model)
    llm_model_id = _resolve_canonical_local_llm_model_id(adapter, effective_requested_model)
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

    return adapter.chat_completion(
        model=llm_model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        allow_local_fallback=allow_local_fallback,
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
