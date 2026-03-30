from __future__ import annotations

from typing import Any

from ..repositories import context_management as context_repo
from .context_management_serialization import _normalize_schema_profile_payload, _serialize_schema_profile
from .platform_types import PlatformControlPlaneError


def list_schema_profiles(database_url: str, *, provider_key: str) -> list[dict[str, Any]]:
    return [
        _serialize_schema_profile(row)
        for row in context_repo.list_schema_profiles(database_url, provider_key=provider_key)
    ]


def create_schema_profile(
    database_url: str,
    *,
    payload: dict[str, Any],
    created_by_user_id: int | None,
) -> dict[str, Any]:
    normalized = _normalize_schema_profile_payload(database_url, payload)
    existing = context_repo.get_schema_profile_by_provider_and_slug(
        database_url,
        provider_key=normalized["provider_key"],
        slug=normalized["slug"],
    )
    if existing is not None:
        raise PlatformControlPlaneError(
            "schema_profile_slug_conflict",
            "A schema profile with this slug already exists for the selected provider family",
            status_code=409,
            details={
                "provider_key": normalized["provider_key"],
                "slug": normalized["slug"],
            },
        )
    profile = context_repo.create_schema_profile(
        database_url,
        slug=normalized["slug"],
        display_name=normalized["display_name"],
        description=normalized["description"],
        provider_key=normalized["provider_key"],
        is_system=False,
        schema_json=normalized["schema"],
        created_by_user_id=created_by_user_id,
    )
    return _serialize_schema_profile(profile)
