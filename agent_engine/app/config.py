from __future__ import annotations

import os
from dataclasses import dataclass

RUNTIME_PROFILES = {"online", "offline", "air_gapped"}
DEFAULT_RUNTIME_PROFILE = "offline"
DEFAULT_AGENT_ENGINE_SERVICE_TOKEN = "dev-agent-engine-token"


@dataclass(frozen=True)
class EngineConfig:
    database_url: str
    runtime_profile_override: str
    agent_engine_service_token: str


def get_config() -> EngineConfig:
    return EngineConfig(
        database_url=os.getenv("DATABASE_URL", "").strip(),
        runtime_profile_override=(
            os.getenv("VANESSA_RUNTIME_PROFILE", DEFAULT_RUNTIME_PROFILE).strip().lower() or DEFAULT_RUNTIME_PROFILE
        ),
        agent_engine_service_token=(
            os.getenv("AGENT_ENGINE_SERVICE_TOKEN", DEFAULT_AGENT_ENGINE_SERVICE_TOKEN).strip()
            or DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
        ),
    )

