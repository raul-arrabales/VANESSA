from __future__ import annotations

import os
from dataclasses import dataclass

RUNTIME_PROFILES = {"online", "offline", "air_gapped"}
DEFAULT_RUNTIME_PROFILE = "offline"
DEFAULT_AGENT_ENGINE_SERVICE_TOKEN = "dev-agent-engine-token"


@dataclass(frozen=True)
class EngineConfig:
    database_url: str
    runtime_profile_override: str | None
    agent_engine_service_token: str


def _get_runtime_profile_override_env() -> str | None:
    value = os.getenv("VANESSA_RUNTIME_PROFILE")
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in RUNTIME_PROFILES:
        return normalized
    return None


def get_config() -> EngineConfig:
    return EngineConfig(
        database_url=os.getenv("DATABASE_URL", "").strip(),
        runtime_profile_override=_get_runtime_profile_override_env(),
        agent_engine_service_token=(
            os.getenv("AGENT_ENGINE_SERVICE_TOKEN", DEFAULT_AGENT_ENGINE_SERVICE_TOKEN).strip()
            or DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
        ),
    )
