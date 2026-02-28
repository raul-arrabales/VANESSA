from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.config import (  # noqa: E402
    DEFAULT_AGENT_ENGINE_SERVICE_TOKEN,
    get_config,
)


def test_engine_config_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE", raising=False)
    monkeypatch.delenv("AGENT_ENGINE_SERVICE_TOKEN", raising=False)

    config = get_config()
    assert config.database_url == ""
    assert config.runtime_profile_override is None
    assert config.agent_engine_service_token == DEFAULT_AGENT_ENGINE_SERVICE_TOKEN


def test_engine_config_env_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "air_gapped")
    monkeypatch.setenv("AGENT_ENGINE_SERVICE_TOKEN", "custom-token")

    config = get_config()
    assert config.database_url == "postgresql://example"
    assert config.runtime_profile_override == "air_gapped"
    assert config.agent_engine_service_token == "custom-token"



def test_engine_config_invalid_runtime_profile_is_ignored(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "invalid")

    config = get_config()
    assert config.runtime_profile_override is None
