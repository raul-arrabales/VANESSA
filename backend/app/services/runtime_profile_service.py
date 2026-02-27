from __future__ import annotations

import os

from ..repositories.registry import get_runtime_profile, upsert_runtime_profile

RUNTIME_PROFILES = {"online", "offline", "air_gapped"}
_DEFAULT_PROFILE = "offline"


def resolve_runtime_profile(database_url: str) -> str:
    # Explicit env override wins to support ops and deterministic staging behavior.
    env_value = os.getenv("VANESSA_RUNTIME_PROFILE", "").strip().lower()
    if env_value in RUNTIME_PROFILES:
        return env_value

    try:
        stored_value = get_runtime_profile(database_url)
        if stored_value in RUNTIME_PROFILES:
            return stored_value
    except Exception:
        # During tests and bootstrap phases the runtime config table may be unavailable.
        pass

    return _DEFAULT_PROFILE


def update_runtime_profile(database_url: str, *, profile: str, updated_by_user_id: int) -> str:
    return upsert_runtime_profile(
        database_url,
        profile=profile,
        updated_by_user_id=updated_by_user_id,
    )


def internet_allowed(profile: str) -> bool:
    normalized = profile.strip().lower()
    return normalized == "online"
