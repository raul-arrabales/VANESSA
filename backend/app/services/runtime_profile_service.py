from __future__ import annotations

from dataclasses import dataclass

from ..config import DEFAULT_RUNTIME_PROFILE, RUNTIME_PROFILES, get_backend_runtime_config
from ..repositories.registry import (
    get_runtime_profile,
    normalize_runtime_profile_state,
    seed_runtime_profile_if_missing,
    upsert_runtime_profile,
)


@dataclass(frozen=True)
class RuntimeProfileState:
    profile: str
    locked: bool
    source: str


class RuntimeProfileLockedError(RuntimeError):
    def __init__(self, profile: str):
        super().__init__(f"Runtime profile is locked to '{profile}' by environment configuration")
        self.profile = profile


def resolve_runtime_profile_state(database_url: str) -> RuntimeProfileState:
    forced_value = get_backend_runtime_config().runtime_profile_force
    if forced_value is not None:
        return RuntimeProfileState(profile=forced_value, locked=True, source="forced")

    try:
        stored_value = get_runtime_profile(database_url)
        if stored_value in RUNTIME_PROFILES:
            return RuntimeProfileState(profile=stored_value, locked=False, source="database")
    except Exception:
        # During tests and bootstrap phases the runtime config table may be unavailable.
        pass

    return RuntimeProfileState(profile=DEFAULT_RUNTIME_PROFILE, locked=False, source="default")


def resolve_runtime_profile(database_url: str) -> str:
    return resolve_runtime_profile_state(database_url).profile


def seed_runtime_profile_from_config(database_url: str) -> str | None:
    normalize_runtime_profile_state(database_url)
    seed_profile = get_backend_runtime_config().runtime_profile_seed or DEFAULT_RUNTIME_PROFILE
    return seed_runtime_profile_if_missing(database_url, profile=seed_profile)


def update_runtime_profile(database_url: str, *, profile: str, updated_by_user_id: int) -> str:
    forced_value = get_backend_runtime_config().runtime_profile_force
    if forced_value is not None:
        raise RuntimeProfileLockedError(forced_value)
    return upsert_runtime_profile(
        database_url,
        profile=profile,
        updated_by_user_id=updated_by_user_id,
    )


def internet_allowed(profile: str) -> bool:
    normalized = profile.strip().lower()
    return normalized == "online"
