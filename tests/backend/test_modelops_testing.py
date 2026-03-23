from __future__ import annotations

import pytest

from app.config import AuthConfig
from app.services import modelops_testing
from tests.backend.support.auth_harness import build_test_auth_config


@pytest.fixture()
def config() -> AuthConfig:
    return build_test_auth_config(AuthConfig)


def test_run_model_test_persists_successful_cloud_llm_result(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    recorded_test_run: dict[str, object] = {}
    audit_events: list[str] = []

    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
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
        modelops_testing,
        "get_active_credential_secret_by_id",
        lambda *args, **kwargs: {
            "api_base_url": "https://api.example.com/v1",
            "api_key": "sk-test-secret",
        },
    )
    monkeypatch.setattr(
        modelops_testing,
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
    monkeypatch.setattr(modelops_testing, "resolve_runtime_profile", lambda _database_url: "online")
    monkeypatch.setattr(modelops_testing.modelops_repo, "get_model", lambda _database_url, model_id: {"model_id": model_id, "artifact": {}})

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

    monkeypatch.setattr(modelops_testing.modelops_repo, "append_model_test_run", _append_model_test_run)
    monkeypatch.setattr(
        modelops_testing.modelops_repo,
        "append_audit_event",
        lambda _database_url, **kwargs: audit_events.append(str(kwargs["event_type"])),
    )

    result = modelops_testing.run_model_test(
        "postgresql://ignored",
        config=config,
        actor_user_id=1,
        actor_role="superadmin",
        model_id="cloud-model-1",
        inputs={"prompt": "hello"},
    )

    assert recorded_test_run["result"] == modelops_testing.modelops_repo.TEST_SUCCESS
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


def test_run_model_test_allows_superadmin_local_llm_with_exact_runtime_match(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    recorded_test_run: dict[str, object] = {}
    audit_events: list[str] = []

    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "Qwen--Qwen2.5-0.5B-Instruct",
            "lifecycle_state": "registered",
            "backend_kind": "local",
            "hosting_kind": "local",
            "runtime_mode_policy": "online_offline",
            "task_key": "llm",
            "provider_model_id": None,
            "local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
            "current_config_fingerprint": "fingerprint-local-1",
            "artifact": {"storage_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"},
            "metadata": {},
        },
    )
    monkeypatch.setattr(modelops_testing, "resolve_runtime_profile", lambda _database_url: "offline")
    monkeypatch.setattr(
        modelops_testing.platform_repo,
        "list_provider_instances",
        lambda _database_url: [
            {
                "id": "provider-1",
                "slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "capability_key": "llm_inference",
                "adapter_kind": "openai_compatible_llm",
                "display_name": "vLLM local gateway",
                "description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {},
            }
        ],
    )
    monkeypatch.setattr(
        modelops_testing.platform_repo,
        "get_active_binding_for_capability",
        lambda _database_url, capability_key: {"provider_instance_id": "provider-1"},
    )
    monkeypatch.setattr(modelops_testing, "ensure_platform_bootstrap_state", lambda _database_url, _config: None)

    class FakeAdapter:
        def __init__(self):
            self.binding = type("Binding", (), {"enabled": True})()
            self.chat_calls: list[dict[str, object]] = []

        def list_models(self):
            return {
                "data": [
                    {
                        "id": "local-vllm-default",
                        "display_name": "Local vLLM Default",
                        "metadata": {"upstream_model": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"},
                    }
                ]
            }, 200

        def chat_completion(self, *, model, messages, max_tokens, temperature, allow_local_fallback):
            self.chat_calls.append(
                {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "allow_local_fallback": allow_local_fallback,
                }
            )
            return {
                "output": [{"content": [{"type": "text", "text": "local hello back"}]}],
            }, 200

    adapter = FakeAdapter()
    monkeypatch.setattr(
        modelops_testing,
        "resolve_llm_inference_adapter",
        lambda _database_url, _config, provider_instance_id=None: adapter,
    )
    monkeypatch.setattr(
        modelops_testing.modelops_repo,
        "get_model",
        lambda _database_url, model_id: {
            "model_id": model_id,
            "artifact": {"storage_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"},
        },
    )

    def _append_model_test_run(_database_url: str, **kwargs):
        recorded_test_run.update(kwargs)
        return {
            "id": "test-run-local-1",
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

    monkeypatch.setattr(modelops_testing.modelops_repo, "append_model_test_run", _append_model_test_run)
    monkeypatch.setattr(
        modelops_testing.modelops_repo,
        "append_audit_event",
        lambda _database_url, **kwargs: audit_events.append(str(kwargs["event_type"])),
    )

    result = modelops_testing.run_model_test(
        "postgresql://ignored",
        config=config,
        actor_user_id=1,
        actor_role="superadmin",
        model_id="Qwen--Qwen2.5-0.5B-Instruct",
        inputs={"prompt": "hello"},
        provider_instance_id="provider-1",
    )

    assert recorded_test_run["result"] == modelops_testing.modelops_repo.TEST_SUCCESS
    assert recorded_test_run["input_payload"]["provider_instance_id"] == "provider-1"
    assert recorded_test_run["input_payload"]["model"] == "local-vllm-default"
    assert result["result"]["response_text"] == "local hello back"
    assert adapter.chat_calls == [
        {
            "model": "local-vllm-default",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
            "max_tokens": 64,
            "temperature": 0,
            "allow_local_fallback": False,
        }
    ]
    assert audit_events == ["model.tested"]


def test_run_model_test_rejects_local_runtime_when_selected_provider_does_not_serve_model(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    recorded_test_run: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "Qwen--Qwen2.5-0.5B-Instruct",
            "lifecycle_state": "registered",
            "backend_kind": "local",
            "hosting_kind": "local",
            "runtime_mode_policy": "online_offline",
            "task_key": "llm",
            "local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
            "current_config_fingerprint": "fingerprint-local-2",
            "artifact": {"storage_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"},
            "metadata": {},
        },
    )
    monkeypatch.setattr(modelops_testing, "resolve_runtime_profile", lambda _database_url: "online")
    monkeypatch.setattr(
        modelops_testing.platform_repo,
        "list_provider_instances",
        lambda _database_url: [
            {
                "id": "provider-1",
                "slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "capability_key": "llm_inference",
                "adapter_kind": "openai_compatible_llm",
                "display_name": "vLLM local gateway",
                "description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {},
            }
        ],
    )
    monkeypatch.setattr(
        modelops_testing.platform_repo,
        "get_active_binding_for_capability",
        lambda _database_url, capability_key: {"provider_instance_id": "provider-1"},
    )
    monkeypatch.setattr(modelops_testing, "ensure_platform_bootstrap_state", lambda _database_url, _config: None)

    class FakeAdapter:
        def list_models(self):
            return {
                "data": [
                    {
                        "id": "local-vllm-default",
                        "display_name": "Local vLLM Default",
                        "metadata": {"upstream_model": "/models/llm/another-model"},
                    }
                ]
            }, 200

    monkeypatch.setattr(
        modelops_testing,
        "resolve_llm_inference_adapter",
        lambda _database_url, _config, provider_instance_id=None: FakeAdapter(),
    )

    def _append_model_test_run(_database_url: str, **kwargs):
        recorded_test_run.update(kwargs)
        return {
            "id": "test-run-local-2",
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

    monkeypatch.setattr(modelops_testing.modelops_repo, "append_model_test_run", _append_model_test_run)

    with pytest.raises(modelops_testing.ModelOpsError) as exc_info:
        modelops_testing.run_model_test(
            "postgresql://ignored",
            config=config,
            actor_user_id=1,
            actor_role="superadmin",
            model_id="Qwen--Qwen2.5-0.5B-Instruct",
            inputs={"prompt": "hello"},
            provider_instance_id="provider-1",
        )

    assert exc_info.value.code == "local_model_not_served_by_runtime"
    assert recorded_test_run["result"] == modelops_testing.modelops_repo.TEST_FAILURE
    assert recorded_test_run["error_details"] == {
        "error": "local_model_not_served_by_runtime",
        "provider_instance_id": "provider-1",
    }


def test_run_model_test_rejects_local_provider_override_for_non_superadmin(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    recorded_test_run: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "Qwen--Qwen2.5-0.5B-Instruct",
            "lifecycle_state": "registered",
            "backend_kind": "local",
            "hosting_kind": "local",
            "runtime_mode_policy": "online_offline",
            "task_key": "llm",
            "local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
            "current_config_fingerprint": "fingerprint-local-3",
            "artifact": {"storage_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"},
            "metadata": {},
        },
    )
    monkeypatch.setattr(modelops_testing, "resolve_runtime_profile", lambda _database_url: "online")

    def _append_model_test_run(_database_url: str, **kwargs):
        recorded_test_run.update(kwargs)
        return {
            "id": "test-run-local-3",
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

    monkeypatch.setattr(modelops_testing.modelops_repo, "append_model_test_run", _append_model_test_run)

    with pytest.raises(modelops_testing.ModelOpsError) as exc_info:
        modelops_testing.run_model_test(
            "postgresql://ignored",
            config=config,
            actor_user_id=7,
            actor_role="admin",
            model_id="Qwen--Qwen2.5-0.5B-Instruct",
            inputs={"prompt": "hello"},
            provider_instance_id="provider-1",
        )

    assert exc_info.value.code == "local_model_runtime_selection_required"
    assert recorded_test_run["error_details"] == {"error": "local_model_runtime_selection_required"}


def test_validate_model_requires_successful_matching_test_run(monkeypatch: pytest.MonkeyPatch, config: AuthConfig):
    recorded_validation: dict[str, object] = {}

    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "cloud-model-1",
            "lifecycle_state": "registered",
            "is_validation_current": False,
            "last_validation_status": "failure",
            "task_key": "llm",
            "current_config_fingerprint": "fingerprint-1",
        },
    )
    monkeypatch.setattr(
        modelops_testing.modelops_repo,
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

    monkeypatch.setattr(modelops_testing.modelops_repo, "append_validation", _append_validation)
    monkeypatch.setattr(modelops_testing.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(modelops_testing.modelops_repo, "get_model", lambda _database_url, model_id: {"model_id": model_id, "artifact": {}})

    payload = modelops_testing.validate_model(
        "postgresql://ignored",
        config=config,
        actor_user_id=1,
        actor_role="superadmin",
        model_id="cloud-model-1",
        test_run_id="test-run-1",
    )

    assert recorded_validation["validator_kind"] == "llm_test_confirmation"
    assert recorded_validation["result"] == modelops_testing.modelops_repo.VALIDATION_SUCCESS
    assert recorded_validation["error_details"] == {"test_run_id": "test-run-1"}
    assert payload["validation"]["result"] == "success"


def test_validate_model_rejects_when_validation_is_already_current(
    monkeypatch: pytest.MonkeyPatch,
    config: AuthConfig,
):
    monkeypatch.setattr(
        modelops_testing,
        "get_accessible_model",
        lambda *args, **kwargs: {
            "model_id": "cloud-model-1",
            "lifecycle_state": "active",
            "is_validation_current": True,
            "last_validation_status": "success",
            "task_key": "llm",
            "current_config_fingerprint": "fingerprint-1",
        },
    )

    with pytest.raises(modelops_testing.ModelOpsError) as exc_info:
        modelops_testing.validate_model(
            "postgresql://ignored",
            config=config,
            actor_user_id=1,
            actor_role="superadmin",
            model_id="cloud-model-1",
            test_run_id="test-run-1",
        )

    assert exc_info.value.code == "validation_already_current"
    assert exc_info.value.status_code == 409
