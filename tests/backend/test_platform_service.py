from __future__ import annotations

import pytest

from app.services import platform_adapters, platform_service  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError  # noqa: E402


def test_resolve_llm_inference_adapter_uses_active_binding(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_active_binding_for_capability",
        lambda _db, *, capability_key: {
            "capability_key": capability_key,
            "provider_instance_id": "provider-1",
            "provider_slug": "vllm-local-gateway",
            "provider_key": "vllm_local",
            "provider_display_name": "vLLM local gateway",
            "provider_description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {"chat_completion_path": "/v1/chat/completions"},
            "binding_config": {},
            "adapter_kind": "openai_compatible_llm",
            "deployment_profile_id": "deployment-1",
            "deployment_profile_slug": "local-default",
            "deployment_profile_display_name": "Local Default",
        },
    )

    adapter = platform_service.resolve_llm_inference_adapter("ignored", object())  # type: ignore[arg-type]

    assert isinstance(adapter, platform_adapters.OpenAICompatibleLlmAdapter)
    assert adapter.binding.provider_slug == "vllm-local-gateway"


def test_create_deployment_profile_rejects_provider_capability_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_id: {
            "id": provider_id,
            "capability_key": "vector_store",
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        platform_service.create_deployment_profile(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            payload={
                "slug": "profile-a",
                "display_name": "Profile A",
                "bindings": [
                    {"capability": "llm_inference", "provider_id": "provider-1"},
                ],
            },
            created_by_user_id=1,
        )

    assert exc_info.value.code == "provider_capability_mismatch"


def test_activate_deployment_profile_requires_all_required_capabilities(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_deployment_profile",
        lambda _db, deployment_profile_id: {"id": deployment_profile_id, "slug": "profile-a"},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [
            {"capability_key": "llm_inference", "provider_instance_id": "provider-1", "enabled": True},
        ],
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        platform_service.activate_deployment_profile(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            deployment_profile_id="deployment-1",
            activated_by_user_id=1,
        )

    assert exc_info.value.code == "deployment_profile_incomplete"
    assert exc_info.value.details["missing_capabilities"] == ["vector_store"]


def test_openai_adapter_retries_local_fallback_on_model_not_found(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        assert method == "POST"
        calls.append(dict(payload or {}))
        if payload and payload.get("model") == "Qwen--Qwen2.5-0.5B-Instruct":
            return {"detail": {"code": "model_not_found"}}, 404
        return {"output": [{"content": [{"type": "text", "text": "ok"}]}]}, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.OpenAICompatibleLlmAdapter(
        platform_service.ProviderBinding(
            capability_key="llm_inference",
            provider_instance_id="provider-1",
            provider_slug="vllm-local-gateway",
            provider_key="vllm_local",
            provider_display_name="vLLM local gateway",
            provider_description="desc",
            endpoint_url="http://llm:8000",
            healthcheck_url="http://llm:8000/health",
            enabled=True,
            adapter_kind="openai_compatible_llm",
            config={"local_fallback_model_id": "local-vllm-default"},
            binding_config={},
            deployment_profile_id="deployment-1",
            deployment_profile_slug="local-default",
            deployment_profile_display_name="Local Default",
        )
    )

    payload, status_code = adapter.chat_completion(
        model="Qwen--Qwen2.5-0.5B-Instruct",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        max_tokens=None,
        temperature=None,
        allow_local_fallback=True,
    )

    assert status_code == 200
    assert payload is not None
    assert [call["model"] for call in calls] == [
        "Qwen--Qwen2.5-0.5B-Instruct",
        "local-vllm-default",
    ]
