from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from .platform_service import resolve_embeddings_adapter
from .platform_types import PlatformControlPlaneError


def embed_text_inputs(database_url: str, config: AuthConfig, texts: list[str]) -> dict[str, Any]:
    normalized_texts = _normalize_inputs(texts)
    adapter = resolve_embeddings_adapter(database_url, config)
    payload, status_code = adapter.embed_texts(texts=normalized_texts)
    if payload is None or not 200 <= status_code < 300:
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
