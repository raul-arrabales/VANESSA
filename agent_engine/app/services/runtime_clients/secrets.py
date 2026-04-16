from __future__ import annotations

import os
from typing import Any

from .base import RuntimeClientError


def openai_compatible_headers(
    binding: dict[str, Any],
    *,
    error_cls: type[RuntimeClientError],
) -> dict[str, str]:
    secret_refs = binding.get("config", {}).get("secret_refs") if isinstance(binding.get("config"), dict) else {}
    if not isinstance(secret_refs, dict):
        return {}
    api_key_ref = str(secret_refs.get("api_key") or "").strip()
    if not api_key_ref:
        return {}
    api_key = resolve_secret_ref(api_key_ref)
    if not api_key:
        raise error_cls(
            code="provider_secret_missing",
            message="Provider secret ref could not be resolved",
            status_code=409,
            details={"provider_slug": binding.get("slug"), "secret_ref": api_key_ref},
        )
    return {"Authorization": f"Bearer {api_key}"}


def resolve_secret_ref(reference: str) -> str | None:
    normalized_reference = reference.strip()
    if not normalized_reference:
        return None
    if normalized_reference.startswith("env://"):
        env_name = normalized_reference.removeprefix("env://").strip()
        return os.getenv(env_name, "").strip() or None
    if normalized_reference.startswith("modelops://"):
        return None
    return normalized_reference
