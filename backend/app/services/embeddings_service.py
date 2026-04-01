from __future__ import annotations

import re
from typing import Any

from ..repositories import platform_control_plane as platform_repo
from . import platform_adapters
from .platform_local_slots import recover_provider_local_slot_runtime
from ..config import AuthConfig
from .platform_service import resolve_embeddings_adapter
from .platform_serialization import _runtime_identifier_for_resource
from .platform_types import PlatformControlPlaneError


def embed_text_inputs(
    database_url: str,
    config: AuthConfig,
    texts: list[str],
) -> dict[str, Any]:
    return embed_text_inputs_with_target(database_url, config, texts)


def embed_text_inputs_with_target(
    database_url: str,
    config: AuthConfig,
    texts: list[str],
    *,
    provider_instance_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    normalized_texts = _normalize_inputs(texts)
    adapter = resolve_embeddings_adapter(database_url, config, provider_instance_id=provider_instance_id)
    payload, status_code = adapter.embed_texts(texts=normalized_texts, model=model)
    provider_row = platform_repo.get_provider_instance(database_url, adapter.binding.provider_instance_id)
    recovery_inspection: dict[str, Any] | None = None
    recovery_attempted = False
    should_force_recovery = status_code == 404 and platform_adapters._is_model_not_found(payload)  # type: ignore[attr-defined]
    if isinstance(provider_row, dict):
        _, recovery_attempted, recovery_inspection = recover_provider_local_slot_runtime(
            database_url,
            provider_row=provider_row,
            force=should_force_recovery,
        )
        if recovery_attempted:
            adapter = resolve_embeddings_adapter(database_url, config, provider_instance_id=provider_instance_id)
            payload, status_code = adapter.embed_texts(texts=normalized_texts, model=model)

    if payload is None or not 200 <= status_code < 300:
        if _is_actionable_local_embeddings_runtime_failure(
            provider_row=provider_row,
            recovery_inspection=recovery_inspection,
            payload=payload,
            status_code=status_code,
        ):
            runtime_state = (
                dict(recovery_inspection.get("runtime_state") or {})
                if isinstance(recovery_inspection, dict)
                else {}
            )
            raise PlatformControlPlaneError(
                "embeddings_runtime_drift",
                "Unable to generate embeddings because the local embeddings runtime is empty or out of sync with the configured provider slot.",
                status_code=503,
                details={
                    "status_code": status_code,
                    "provider": adapter.binding.provider_slug,
                    "loaded_managed_model_id": recovery_inspection.get("slot", {}).get("loaded_managed_model_id")
                    if isinstance(recovery_inspection, dict)
                    else None,
                    "expected_runtime_model_id": recovery_inspection.get("runtime_model_id")
                    if isinstance(recovery_inspection, dict)
                    else None,
                    "runtime_inventory_ids": recovery_inspection.get("runtime_inventory_ids")
                    if isinstance(recovery_inspection, dict)
                    else [],
                    "runtime_state": runtime_state,
                    "recovery_attempted": recovery_attempted,
                },
            )
        oversized_input_details = _embeddings_input_too_large_details(payload, status_code)
        if oversized_input_details is not None:
            raise PlatformControlPlaneError(
                "embeddings_input_too_large",
                "Unable to generate embeddings because at least one input exceeds the configured embeddings model context limit. Reduce chunk size before retrying.",
                status_code=400,
                details={
                    "status_code": status_code,
                    "provider": adapter.binding.provider_slug,
                    **oversized_input_details,
                },
            )
        raise PlatformControlPlaneError(
            "embeddings_request_failed",
            "Unable to generate embeddings",
            status_code=502 if status_code < 500 else status_code,
            details={"status_code": status_code, "provider": adapter.binding.provider_slug},
        )

    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(normalized_texts):
        raise PlatformControlPlaneError(
            "embeddings_response_invalid",
            "Embeddings provider returned an invalid response",
            status_code=502,
            details={"provider": adapter.binding.provider_slug},
        )

    dimension = payload.get("embedding_dimension")
    normalized_dimension = int(dimension) if isinstance(dimension, int) else len(embeddings[0]) if embeddings else 0
    return {
        "provider": {
            "id": adapter.binding.provider_instance_id,
            "slug": adapter.binding.provider_slug,
            "provider_key": adapter.binding.provider_key,
            "display_name": adapter.binding.provider_display_name,
            "deployment_profile_slug": adapter.binding.deployment_profile_slug,
            "default_resource_id": adapter.binding.default_resource_id,
        },
        "resource_id": str(model or _runtime_identifier_for_resource(adapter.binding.default_resource or {})).strip() or None,
        "count": len(embeddings),
        "dimension": normalized_dimension,
        "embeddings": embeddings,
    }


def embed_platform_inputs(database_url: str, config: AuthConfig, payload: dict[str, Any]) -> dict[str, Any]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise PlatformControlPlaneError("invalid_inputs", "inputs must be a non-empty array", status_code=400)
    return embed_text_inputs(database_url, config, [str(item) if item is not None else "" for item in inputs])


def _normalize_inputs(texts: list[str]) -> list[str]:
    normalized: list[str] = []
    for index, item in enumerate(texts):
        text = str(item).strip()
        if not text:
            raise PlatformControlPlaneError(
                "invalid_input_text",
                f"inputs[{index}] must be a non-empty string",
                status_code=400,
            )
        normalized.append(text)
    if not normalized:
        raise PlatformControlPlaneError("invalid_inputs", "inputs must be a non-empty array", status_code=400)
    return normalized


def _is_actionable_local_embeddings_runtime_failure(
    *,
    provider_row: dict[str, Any] | None,
    recovery_inspection: dict[str, Any] | None,
    payload: dict[str, Any] | None,
    status_code: int,
) -> bool:
    if not isinstance(provider_row, dict):
        return False
    if str(provider_row.get("provider_key") or "").strip().lower() != "vllm_embeddings_local":
        return False
    if not isinstance(recovery_inspection, dict):
        return False
    if not bool(recovery_inspection.get("has_persisted_intent")):
        return False
    if bool(recovery_inspection.get("runtime_empty")) or not bool(recovery_inspection.get("target_available")):
        return True
    return status_code == 404 and platform_adapters._is_model_not_found(payload)  # type: ignore[attr-defined]


def _embeddings_input_too_large_details(payload: dict[str, Any] | None, status_code: int) -> dict[str, Any] | None:
    if status_code != 400 or not isinstance(payload, dict):
        return None
    detail = payload.get("detail")
    if isinstance(detail, dict):
        raw_message = str(detail.get("message") or detail.get("error") or "").strip()
    else:
        raw_message = str(detail or payload.get("error") or payload.get("message") or "").strip()
    message = raw_message.lower()
    if not message:
        return None
    if not (
        "maximum context length" in message
        or "requested" in message and "tokens" in message and "embedding" in message
        or "reduce the length of the input" in message
        or "input too long" in message
    ):
        return None
    parsed: dict[str, Any] = {"provider_message": raw_message}
    match = re.search(
        r"maximum context length is (?P<max_input_tokens>\d+) tokens.*?requested (?P<requested_tokens>\d+) tokens",
        raw_message,
        flags=re.IGNORECASE,
    )
    if match:
        parsed["max_input_tokens"] = int(match.group("max_input_tokens"))
        parsed["requested_tokens"] = int(match.group("requested_tokens"))
    return parsed
