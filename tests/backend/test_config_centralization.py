from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import config as backend_config  # noqa: E402
from agent_engine.app import config as engine_config  # noqa: E402


def test_backend_runtime_config_defaults(monkeypatch: pytest.MonkeyPatch):
    for name in (
        "FRONTEND_URL",
        "BACKEND_URL",
        "LLM_URL",
        "LLM_RUNTIME_URL",
        "AGENT_ENGINE_URL",
        "AGENT_ENGINE_SERVICE_TOKEN",
        "SANDBOX_URL",
        "KWS_URL",
        "WEAVIATE_URL",
        "VANESSA_RUNTIME_PROFILE",
        "KWS_DETECTION_THRESHOLD",
        "KWS_COOLDOWN_MS",
    ):
        monkeypatch.delenv(name, raising=False)

    runtime = backend_config.get_backend_runtime_config()
    assert runtime.frontend_url == backend_config.DEFAULT_FRONTEND_URL
    assert runtime.backend_url == backend_config.DEFAULT_BACKEND_URL
    assert runtime.llm_url == backend_config.DEFAULT_LLM_URL
    assert runtime.agent_engine_service_token == backend_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    assert runtime.runtime_profile_override is None


def test_backend_and_engine_token_defaults_are_aligned():
    assert (
        backend_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
        == engine_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    )


def test_backend_and_engine_runtime_profiles_are_aligned():
    assert backend_config.RUNTIME_PROFILES == engine_config.RUNTIME_PROFILES
    assert backend_config.DEFAULT_RUNTIME_PROFILE == engine_config.DEFAULT_RUNTIME_PROFILE



def test_backend_runtime_profile_override_ignores_invalid_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "invalid")

    runtime = backend_config.get_backend_runtime_config()
    assert runtime.runtime_profile_override is None
