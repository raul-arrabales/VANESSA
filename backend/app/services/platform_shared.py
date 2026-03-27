from __future__ import annotations

from typing import Any

from .platform_service_types import _TASK_KEY_EMBEDDINGS, _TASK_KEY_LLM
from .platform_types import CAPABILITY_EMBEDDINGS, CAPABILITY_LLM_INFERENCE


def _runtime_model_entries_for_capability(
    capability_key: str,
    payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw_items = payload.get("data")
    if not isinstance(raw_items, list):
        return []
    normalized_capability = capability_key.strip().lower()
    filtered: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
        supports_text = bool(capabilities.get("text"))
        supports_embeddings = bool(capabilities.get("embeddings"))
        include_item = False
        if normalized_capability == CAPABILITY_LLM_INFERENCE:
            include_item = supports_text
        elif normalized_capability == CAPABILITY_EMBEDDINGS:
            include_item = supports_embeddings
        if include_item and str(item.get("id") or "").strip():
            filtered.append(dict(item))
    return filtered


def _expected_task_key(capability_key: str) -> str:
    return _TASK_KEY_LLM if capability_key == CAPABILITY_LLM_INFERENCE else _TASK_KEY_EMBEDDINGS
