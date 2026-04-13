from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services import modelops_cloud_discovery
from app.services.modelops_common import ModelOpsError
from tests.backend.support.auth_harness import build_test_auth_config


@pytest.fixture()
def config() -> AuthConfig:
    return build_test_auth_config(AuthConfig)


def test_discover_cloud_provider_models_lists_openai_compatible_models(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    request_call: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_cloud_discovery,
        "get_active_credential_secret",
        lambda *args, **kwargs: {
            "id": "cred-1",
            "provider_slug": "openai_compatible",
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-secret",
        },
    )

    def _http_json_request(url: str, **kwargs):
        request_call.update({"url": url, **kwargs})
        return {
            "data": [
                {"id": "gpt-4.1", "object": "model", "created": 1715367049, "owned_by": "openai"},
                {"id": "text-embedding-3-small", "object": "model", "created": 1715367049, "owned_by": "openai"},
            ]
        }, 200

    monkeypatch.setattr(modelops_cloud_discovery, "http_json_request", _http_json_request)

    result = modelops_cloud_discovery.discover_cloud_provider_models(
        "postgresql://ignored",
        config=config,
        actor_user_id=7,
        actor_role="user",
        provider="openai_compatible",
        credential_id="00000000-0000-0000-0000-000000000001",
    )

    assert request_call["url"] == "https://api.example.com/v1/models"
    assert request_call["method"] == "GET"
    assert request_call["headers"] == {"Authorization": "Bearer sk-secret"}
    assert result["provider"] == "openai_compatible"
    assert result["credential_id"] == "00000000-0000-0000-0000-000000000001"
    assert result["models"] == [
        {
            "provider_model_id": "gpt-4.1",
            "name": "gpt-4.1",
            "owned_by": "openai",
            "created_at": "2024-05-10T18:50:49+00:00",
            "task_key": "llm",
            "category": "generative",
            "metadata": {
                "provider_model_id": "gpt-4.1",
                "owned_by": "openai",
                "created": 1715367049,
                "object": "model",
            },
        },
        {
            "provider_model_id": "text-embedding-3-small",
            "name": "text-embedding-3-small",
            "owned_by": "openai",
            "created_at": "2024-05-10T18:50:49+00:00",
            "task_key": "embeddings",
            "category": "predictive",
            "metadata": {
                "provider_model_id": "text-embedding-3-small",
                "owned_by": "openai",
                "created": 1715367049,
                "object": "model",
            },
        },
    ]


def test_discover_cloud_provider_models_uses_default_openai_base_url(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    request_call: dict[str, object] = {}
    monkeypatch.setattr(
        modelops_cloud_discovery,
        "get_active_credential_secret",
        lambda *args, **kwargs: {
            "provider_slug": "openai",
            "api_base_url": None,
            "api_key": "sk-secret",
        },
    )

    def _http_json_request(url: str, **kwargs):
        request_call.update({"url": url, **kwargs})
        return {"data": []}, 200

    monkeypatch.setattr(modelops_cloud_discovery, "http_json_request", _http_json_request)

    modelops_cloud_discovery.discover_cloud_provider_models(
        "postgresql://ignored",
        config=config,
        actor_user_id=7,
        actor_role="user",
        provider="openai",
        credential_id="00000000-0000-0000-0000-000000000001",
    )

    assert request_call["url"] == "https://api.openai.com/v1/models"


def test_discover_cloud_provider_models_rejects_unsupported_provider(config: AuthConfig):
    with pytest.raises(ModelOpsError) as exc_info:
        modelops_cloud_discovery.discover_cloud_provider_models(
            "postgresql://ignored",
            config=config,
            actor_user_id=7,
            actor_role="user",
            provider="anthropic",
            credential_id="00000000-0000-0000-0000-000000000001",
        )

    assert exc_info.value.code == "provider_discovery_unsupported"
    assert exc_info.value.status_code == 409


def test_discover_cloud_provider_models_rejects_missing_credential(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    monkeypatch.setattr(modelops_cloud_discovery, "get_active_credential_secret", lambda *args, **kwargs: None)

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_cloud_discovery.discover_cloud_provider_models(
            "postgresql://ignored",
            config=config,
            actor_user_id=7,
            actor_role="user",
            provider="openai",
            credential_id="00000000-0000-0000-0000-000000000001",
        )

    assert exc_info.value.code == "missing_config"


def test_discover_cloud_provider_models_rejects_provider_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    monkeypatch.setattr(
        modelops_cloud_discovery,
        "get_active_credential_secret",
        lambda *args, **kwargs: {"provider_slug": "openai", "api_base_url": "https://api.openai.com/v1", "api_key": "sk-secret"},
    )

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_cloud_discovery.discover_cloud_provider_models(
            "postgresql://ignored",
            config=config,
            actor_user_id=7,
            actor_role="user",
            provider="openai_compatible",
            credential_id="00000000-0000-0000-0000-000000000001",
        )

    assert exc_info.value.code == "credential_provider_mismatch"


def test_discover_cloud_provider_models_hides_upstream_error_payload(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    monkeypatch.setattr(
        modelops_cloud_discovery,
        "get_active_credential_secret",
        lambda *args, **kwargs: {
            "provider_slug": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "sk-secret",
        },
    )
    monkeypatch.setattr(
        modelops_cloud_discovery,
        "http_json_request",
        lambda *args, **kwargs: ({"error": {"message": "bad key sk-secret"}}, 401),
    )

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_cloud_discovery.discover_cloud_provider_models(
            "postgresql://ignored",
            config=config,
            actor_user_id=7,
            actor_role="user",
            provider="openai",
            credential_id="00000000-0000-0000-0000-000000000001",
        )

    assert exc_info.value.code == "provider_model_discovery_failed"
    assert exc_info.value.status_code == 502
    assert "sk-secret" not in exc_info.value.message
    assert "sk-secret" not in str(exc_info.value.details)
