from __future__ import annotations

import os
from dataclasses import dataclass

RUNTIME_PROFILES = {"online", "offline"}
DEFAULT_RUNTIME_PROFILE = "offline"
DEFAULT_AGENT_ENGINE_SERVICE_TOKEN = "dev-agent-engine-token"
DEFAULT_MCP_GATEWAY_SERVICE_TOKEN = "dev-mcp-gateway-token"
DEFAULT_BACKEND_URL = "http://backend:5000"
_LEGACY_RUNTIME_PROFILES = {"air_gapped": "offline"}


@dataclass(frozen=True)
class EngineConfig:
    database_url: str
    runtime_profile_force: str | None
    agent_engine_service_token: str
    mcp_gateway_service_token: str
    backend_url: str


def _get_runtime_profile_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    normalized = value.strip().lower()
    legacy_normalized = _LEGACY_RUNTIME_PROFILES.get(normalized)
    if legacy_normalized is not None:
        print(
            f"[WARN] {name}={normalized} is deprecated; normalizing runtime profile to '{legacy_normalized}'."
        )
        return legacy_normalized
    if normalized in RUNTIME_PROFILES:
        return normalized
    return None


def get_config() -> EngineConfig:
    return EngineConfig(
        database_url=os.getenv("DATABASE_URL", "").strip(),
        runtime_profile_force=_get_runtime_profile_env("VANESSA_RUNTIME_PROFILE_FORCE"),
        agent_engine_service_token=(
            os.getenv("AGENT_ENGINE_SERVICE_TOKEN", DEFAULT_AGENT_ENGINE_SERVICE_TOKEN).strip()
            or DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
        ),
        mcp_gateway_service_token=(
            os.getenv("MCP_GATEWAY_SERVICE_TOKEN", DEFAULT_MCP_GATEWAY_SERVICE_TOKEN).strip()
            or DEFAULT_MCP_GATEWAY_SERVICE_TOKEN
        ),
        backend_url=os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip() or DEFAULT_BACKEND_URL,
    )
