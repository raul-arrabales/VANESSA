from __future__ import annotations

from ..config import DEFAULT_RUNTIME_PROFILE, RUNTIME_PROFILES, get_backend_runtime_config
from ..repositories.registry import get_runtime_profile, upsert_runtime_profile


def resolve_runtime_profile(database_url: str) -> str:
    # Explicit env override wins to support ops and deterministic staging behavior.
    env_value = get_backend_runtime_config().runtime_profile_override
    if env_value is not None:
        return env_value

    try:
        stored_value = get_runtime_profile(database_url)
        if stored_value in RUNTIME_PROFILES:
            return stored_value
    except Exception:
        # During tests and bootstrap phases the runtime config table may be unavailable.
        pass

    return DEFAULT_RUNTIME_PROFILE


def update_runtime_profile(database_url: str, *, profile: str, updated_by_user_id: int) -> str:
    return upsert_runtime_profile(
        database_url,
        profile=profile,
        updated_by_user_id=updated_by_user_id,
    )


def internet_allowed(profile: str) -> bool:
    normalized = profile.strip().lower()
    return normalized == "online"
