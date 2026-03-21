from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services import modelops_service
from tests.backend.support.auth_harness import build_test_auth_config


@pytest.fixture()
def config() -> AuthConfig:
    return build_test_auth_config(AuthConfig)


def test_create_model_accepts_extensible_task_key(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_service,
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

    monkeypatch.setattr(modelops_service.modelops_repo, "upsert_model_record", _upsert_model_record)
    monkeypatch.setattr(modelops_service.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)

    model = modelops_service.create_model(
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
        modelops_service,
        "_get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "model-1",
            "lifecycle_state": "registered",
            "is_validation_current": False,
            "last_validation_status": None,
            "runtime_mode_policy": "online_offline",
        },
    )

    with pytest.raises(modelops_service.ModelOpsError) as exc_info:
        modelops_service.activate_model(
            "postgresql://ignored",
            config=config,
            actor_user_id=1,
            actor_role="superadmin",
            model_id="model-1",
        )

    assert exc_info.value.code == "validation_failed"


def test_ensure_model_invokable_blocks_online_only_models_offline(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    monkeypatch.setattr(
        modelops_service,
        "get_model_detail",
        lambda *args, **kwargs: {
            "id": "cloud-model-1",
            "lifecycle_state": "active",
            "is_validation_current": True,
            "last_validation_status": "success",
            "runtime_mode_policy": "online_only",
        },
    )
    monkeypatch.setattr(modelops_service, "resolve_runtime_profile", lambda _database_url: "offline")

    with pytest.raises(modelops_service.ModelOpsError) as exc_info:
        modelops_service.ensure_model_invokable(
            "postgresql://ignored",
            config=config,
            user_id=4,
            user_role="user",
            model_id="cloud-model-1",
        )

    assert exc_info.value.code == "offline_not_allowed"


def test_run_model_test_persists_successful_cloud_llm_result(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    recorded_test_run: dict[str, object] = {}
    audit_events: list[str] = []

    monkeypatch.setattr(
        modelops_service,
        "_get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "cloud-model-1",
            "lifecycle_state": "registered",
            "backend_kind": "external_api",
            "hosting_kind": "cloud",
            "runtime_mode_policy": "online_only",
            "task_key": "llm",
            "provider_model_id": "gpt-4.1-mini",
            "credential_id": "cred-1",
            "current_config_fingerprint": "fingerprint-1",
            "artifact": {},
        },
    )
    monkeypatch.setattr(
        modelops_service,
        "get_active_credential_secret",
        lambda *args, **kwargs: {
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-secret",
        },
    )
    monkeypatch.setattr(
        modelops_service,
        "http_json_request",
        lambda *args, **kwargs: (
            {
                "choices": [
                    {
                        "message": {
                            "content": "hello back",
                        }
                    }
                ]
            },
            200,
        ),
    )
    monkeypatch.setattr(modelops_service, "resolve_runtime_profile", lambda _database_url: "online")
    monkeypatch.setattr(modelops_service.modelops_repo, "get_model", lambda _database_url, model_id: {"model_id": model_id, "artifact": {}})

    def _append_model_test_run(_database_url: str, **kwargs):
        recorded_test_run.update(kwargs)
        return {
            "id": "test-run-1",
            "model_id": kwargs["model_id"],
            "task_key": kwargs["task_key"],
            "result": kwargs["result"],
            "summary": kwargs["summary"],
            "input_payload": kwargs["input_payload"],
            "output_payload": kwargs["output_payload"],
            "error_details": kwargs["error_details"],
            "latency_ms": kwargs["latency_ms"],
            "config_fingerprint": kwargs["config_fingerprint"],
        }

    monkeypatch.setattr(modelops_service.modelops_repo, "append_model_test_run", _append_model_test_run)
    monkeypatch.setattr(
        modelops_service.modelops_repo,
        "append_audit_event",
        lambda _database_url, **kwargs: audit_events.append(str(kwargs["event_type"])),
    )

    result = modelops_service.run_model_test(
        "postgresql://ignored",
        config=config,
        actor_user_id=1,
        actor_role="superadmin",
        model_id="cloud-model-1",
        inputs={"prompt": "hello"},
    )

    assert recorded_test_run["result"] == modelops_service.modelops_repo.TEST_SUCCESS
    assert recorded_test_run["task_key"] == "llm"
    assert recorded_test_run["input_payload"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0,
        "max_tokens": 64,
    }
    assert result["test_run"]["id"] == "test-run-1"
    assert result["result"]["response_text"] == "hello back"
    assert audit_events == ["model.tested"]


def test_validate_model_requires_successful_matching_test_run(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    recorded_validation: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_service,
        "_get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "cloud-model-1",
            "lifecycle_state": "registered",
            "task_key": "llm",
            "current_config_fingerprint": "fingerprint-1",
        },
    )
    monkeypatch.setattr(
        modelops_service.modelops_repo,
        "get_model_test_run",
        lambda _database_url, test_run_id: {
            "id": test_run_id,
            "model_id": "cloud-model-1",
            "result": "success",
            "config_fingerprint": "fingerprint-1",
        },
    )

    def _append_validation(_database_url: str, **kwargs):
        recorded_validation.update(kwargs)
        return {
            "validator_kind": kwargs["validator_kind"],
            "result": kwargs["result"],
            "error_details": kwargs["error_details"],
        }

    monkeypatch.setattr(modelops_service.modelops_repo, "append_validation", _append_validation)
    monkeypatch.setattr(modelops_service.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(modelops_service.modelops_repo, "get_model", lambda _database_url, model_id: {"model_id": model_id, "artifact": {}})

    payload = modelops_service.validate_model(
        "postgresql://ignored",
        config=config,
        actor_user_id=1,
        actor_role="superadmin",
        model_id="cloud-model-1",
        test_run_id="test-run-1",
    )

    assert recorded_validation["validator_kind"] == "llm_test_confirmation"
    assert recorded_validation["result"] == modelops_service.modelops_repo.VALIDATION_SUCCESS
    assert recorded_validation["error_details"] == {"test_run_id": "test-run-1"}
    assert payload["validation"]["result"] == "success"
