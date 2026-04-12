from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services import modelops_runtime
from app.services.modelops_common import ModelOpsError
from tests.backend.support.auth_harness import build_test_auth_config


@pytest.fixture()
def config() -> AuthConfig:
    return build_test_auth_config(AuthConfig)


def test_ensure_model_invokable_blocks_online_only_models_offline(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    monkeypatch.setattr(
        modelops_runtime,
        "get_model_detail",
        lambda *args, **kwargs: {
            "id": "cloud-model-1",
            "lifecycle_state": "active",
            "is_validation_current": True,
            "last_validation_status": "success",
            "runtime_mode_policy": "online_only",
        },
    )
    monkeypatch.setattr(modelops_runtime, "resolve_runtime_profile", lambda _database_url: "offline")

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_runtime.ensure_model_invokable(
            "postgresql://ignored",
            config=config,
            user_id=4,
            user_role="user",
            model_id="cloud-model-1",
        )

    assert exc_info.value.code == "offline_not_allowed"


def test_ensure_model_invokable_blocks_revoked_cloud_credential(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    monkeypatch.setattr(
        modelops_runtime,
        "get_model_detail",
        lambda *args, **kwargs: {
            "id": "cloud-model-1",
            "backend": "external_api",
            "lifecycle_state": "active",
            "is_validation_current": True,
            "last_validation_status": "success",
            "runtime_mode_policy": "online_only",
            "credential": {"status": "revoked"},
        },
    )

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_runtime.ensure_model_invokable(
            "postgresql://ignored",
            config=config,
            user_id=4,
            user_role="user",
            model_id="cloud-model-1",
        )

    assert exc_info.value.code == "credential_unavailable"
