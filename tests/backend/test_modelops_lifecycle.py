from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services import modelops_lifecycle
from app.services.modelops_common import ModelOpsError
from tests.backend.support.auth_harness import build_test_auth_config


@pytest.fixture()
def config() -> AuthConfig:
    return build_test_auth_config(AuthConfig)


def test_create_model_accepts_extensible_task_key(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_lifecycle,
        "get_active_credential_secret",
        lambda *args, **kwargs: {
            "id": "cred-1",
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-secret",
        },
    )

    def _upsert_model_record(_database_url: str, **kwargs):
        captured.update(kwargs)
        return {
            "model_id": kwargs["model_id"],
            "global_model_id": f"{kwargs['node_id']}:{kwargs['model_id']}",
            "node_id": kwargs["node_id"],
            "name": kwargs["name"],
            "provider": kwargs["provider"],
            "provider_model_id": kwargs.get("provider_model_id"),
            "backend_kind": kwargs["backend_kind"],
            "hosting_kind": "cloud",
            "source_kind": kwargs["source_kind"],
            "availability": kwargs["availability"],
            "runtime_mode_policy": "online_only",
            "visibility_scope": kwargs["visibility_scope"],
            "owner_type": kwargs["owner_type"],
            "owner_user_id": kwargs["owner_user_id"],
            "task_key": kwargs["task_key"],
            "category": kwargs["category"],
            "lifecycle_state": kwargs["lifecycle_state"],
            "is_validation_current": False,
            "last_validation_status": None,
            "last_validated_at": None,
            "last_validation_error": {},
            "metadata": {},
            "artifact": {},
            "dependencies": [],
        }

    monkeypatch.setattr(modelops_lifecycle.modelops_repo, "upsert_model_record", _upsert_model_record)
    monkeypatch.setattr(modelops_lifecycle.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)

    model = modelops_lifecycle.create_model(
        "postgresql://ignored",
        config=config,
        actor_user_id=7,
        actor_role="user",
        payload={
            "id": "translator-private",
            "name": "Translator Private",
            "provider": "openai_compatible",
            "backend": "external_api",
            "provider_model_id": "gpt-4.1-mini",
            "credential_id": "cred-1",
            "task_key": "translation",
        },
    )

    assert captured["task_key"] == "translation"
    assert captured["category"] == "generative"
    assert captured["owner_type"] == "user"
    assert captured["visibility_scope"] == "private"
    assert model["task_key"] == "translation"
    assert model["category"] == "generative"
    assert model["owner_type"] == "user"


def test_activate_model_requires_current_successful_validation(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    monkeypatch.setattr(
        modelops_lifecycle,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "model-1",
            "lifecycle_state": "registered",
            "is_validation_current": False,
            "last_validation_status": None,
            "runtime_mode_policy": "online_offline",
        },
    )

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_lifecycle.activate_model(
            "postgresql://ignored",
            config=config,
            actor_user_id=1,
            actor_role="superadmin",
            model_id="model-1",
        )

    assert exc_info.value.code == "validation_failed"
