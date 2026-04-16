from __future__ import annotations

from typing import Any

from .platform_types import PlatformControlPlaneError
from .runtime_profile_service import resolve_runtime_profile

PROVIDER_ORIGIN_LOCAL = "local"
PROVIDER_ORIGIN_CLOUD = "cloud"


def normalize_provider_origin(value: Any) -> str:
    normalized = str(value or PROVIDER_ORIGIN_LOCAL).strip().lower()
    return normalized if normalized in {PROVIDER_ORIGIN_LOCAL, PROVIDER_ORIGIN_CLOUD} else PROVIDER_ORIGIN_LOCAL


def is_cloud_provider(row: dict[str, Any]) -> bool:
    return normalize_provider_origin(row.get("provider_origin")) == PROVIDER_ORIGIN_CLOUD


def assert_provider_allowed_for_runtime_profile(
    *,
    runtime_profile: str,
    provider_row: dict[str, Any],
) -> None:
    normalized_profile = str(runtime_profile or "").strip().lower()
    origin = normalize_provider_origin(provider_row.get("provider_origin"))
    if normalized_profile == "online" or origin != PROVIDER_ORIGIN_CLOUD:
        return
    raise PlatformControlPlaneError(
        "offline_provider_blocked",
        "Cloud provider is not available in offline runtime profile",
        status_code=409,
        details={
            "runtime_profile": normalized_profile or "offline",
            "provider_origin": origin,
            "provider_key": str(provider_row.get("provider_key") or "").strip().lower(),
            "provider_instance_id": str(provider_row.get("provider_instance_id") or provider_row.get("id") or "").strip(),
        },
    )


def assert_provider_allowed_for_current_runtime(
    database_url: str,
    provider_row: dict[str, Any],
) -> None:
    if not is_cloud_provider(provider_row):
        return
    assert_provider_allowed_for_runtime_profile(
        runtime_profile=resolve_runtime_profile(database_url),
        provider_row=provider_row,
    )


def assert_bindings_allowed_for_runtime_profile(
    *,
    runtime_profile: str,
    bindings: list[dict[str, Any]],
) -> None:
    for binding in bindings:
        assert_provider_allowed_for_runtime_profile(
            runtime_profile=runtime_profile,
            provider_row=binding,
        )
