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
        "CLOUD_TRAFFIC_LOG_ENABLED",
        "CLOUD_TRAFFIC_LOG_PATH",
        "CLOUD_TRAFFIC_LOG_MAX_BYTES",
        "AGENT_ENGINE_URL",
        "AGENT_ENGINE_SERVICE_TOKEN",
        "SANDBOX_URL",
        "KWS_URL",
        "WEAVIATE_URL",
        "VANESSA_RUNTIME_PROFILE",
        "VANESSA_RUNTIME_PROFILE_FORCE",
        "KWS_DETECTION_THRESHOLD",
        "KWS_COOLDOWN_MS",
    ):
        monkeypatch.delenv(name, raising=False)

    runtime = backend_config.get_backend_runtime_config()
    assert runtime.frontend_url == backend_config.DEFAULT_FRONTEND_URL
    assert runtime.backend_url == backend_config.DEFAULT_BACKEND_URL
    assert runtime.llm_url == backend_config.DEFAULT_LLM_URL
    assert runtime.agent_engine_service_token == backend_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    assert runtime.runtime_profile_seed is None
    assert runtime.runtime_profile_force is None


def test_backend_and_engine_token_defaults_are_aligned():
    assert (
        backend_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
        == engine_config.DEFAULT_AGENT_ENGINE_SERVICE_TOKEN
    )


def test_backend_and_engine_runtime_profiles_are_aligned():
    assert backend_config.RUNTIME_PROFILES == engine_config.RUNTIME_PROFILES
    assert backend_config.DEFAULT_RUNTIME_PROFILE == engine_config.DEFAULT_RUNTIME_PROFILE



def test_backend_runtime_profile_envs_ignore_invalid_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "invalid")
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE_FORCE", "invalid")

    runtime = backend_config.get_backend_runtime_config()
    assert runtime.runtime_profile_seed is None
    assert runtime.runtime_profile_force is None


def test_backend_runtime_profile_envs_normalize_legacy_air_gapped(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "air_gapped")
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE_FORCE", "air_gapped")

    runtime = backend_config.get_backend_runtime_config()
    assert runtime.runtime_profile_seed == "offline"
    assert runtime.runtime_profile_force == "offline"


def test_model_credentials_encryption_key_prefers_dedicated_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://ignored")
    monkeypatch.setenv("AUTH_JWT_SECRET", "jwt-signing-secret")
    monkeypatch.setenv("MODEL_CREDENTIALS_ENCRYPTION_KEY", "model-credential-secret")

    config = backend_config.get_auth_config()
    assert config.model_credentials_encryption_key == "model-credential-secret"


def test_model_credentials_encryption_key_falls_back_to_jwt_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://ignored")
    monkeypatch.setenv("AUTH_JWT_SECRET", "jwt-signing-secret")
    monkeypatch.delenv("MODEL_CREDENTIALS_ENCRYPTION_KEY", raising=False)

    config = backend_config.get_auth_config()
    assert config.model_credentials_encryption_key == "jwt-signing-secret"


def test_cloud_traffic_log_config_defaults_and_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://ignored")
    monkeypatch.setenv("AUTH_JWT_SECRET", "jwt-signing-secret")
    monkeypatch.delenv("CLOUD_TRAFFIC_LOG_ENABLED", raising=False)
    monkeypatch.delenv("CLOUD_TRAFFIC_LOG_PATH", raising=False)
    monkeypatch.delenv("CLOUD_TRAFFIC_LOG_MAX_BYTES", raising=False)

    defaults = backend_config.get_auth_config()
    assert defaults.cloud_traffic_log_enabled is True
    assert defaults.cloud_traffic_log_path == backend_config.DEFAULT_CLOUD_TRAFFIC_LOG_PATH
    assert defaults.cloud_traffic_log_max_bytes == backend_config.DEFAULT_CLOUD_TRAFFIC_LOG_MAX_BYTES

    monkeypatch.setenv("CLOUD_TRAFFIC_LOG_ENABLED", "false")
    monkeypatch.setenv("CLOUD_TRAFFIC_LOG_PATH", "/tmp/cloud.jsonl")
    monkeypatch.setenv("CLOUD_TRAFFIC_LOG_MAX_BYTES", "1234")

    overridden = backend_config.get_auth_config()
    assert overridden.cloud_traffic_log_enabled is False
    assert overridden.cloud_traffic_log_path == "/tmp/cloud.jsonl"
    assert overridden.cloud_traffic_log_max_bytes == 1234


def test_shared_runtime_config_fields_exist_on_both_configs():
    auth_fields = backend_config._config_field_names(backend_config.AuthConfig)
    runtime_fields = backend_config._config_field_names(backend_config.BackendRuntimeConfig)

    assert backend_config.SHARED_RUNTIME_CONFIG_FIELD_NAMES <= auth_fields
    assert backend_config.SHARED_RUNTIME_CONFIG_FIELD_NAMES <= runtime_fields


def test_auth_runtime_extension_fields_exist_on_auth_config():
    auth_fields = backend_config._config_field_names(backend_config.AuthConfig)

    assert backend_config.AUTH_RUNTIME_EXTENSION_FIELD_NAMES <= auth_fields


def test_auth_config_includes_chat_attachments_root(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://ignored")
    monkeypatch.setenv("AUTH_JWT_SECRET", "jwt-signing-secret")
    monkeypatch.setenv("CHAT_ATTACHMENTS_ROOT", "/tmp/chat-attachments")

    config = backend_config.get_auth_config()

    assert config.chat_attachments_root == "/tmp/chat-attachments"
