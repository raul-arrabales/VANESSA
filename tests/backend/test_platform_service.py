from __future__ import annotations

from types import SimpleNamespace

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
    assert exc_info.value.details["missing_capabilities"] == ["embeddings", "vector_store"]


def test_activate_deployment_profile_rejects_failed_preflight_validation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_deployment_profile",
        lambda _db, deployment_profile_id: {"id": deployment_profile_id, "slug": "profile-a", "is_active": False},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [
            {"capability_key": "llm_inference", "provider_instance_id": "provider-1", "enabled": True},
            {"capability_key": "embeddings", "provider_instance_id": "provider-embeddings", "enabled": True},
            {"capability_key": "vector_store", "provider_instance_id": "provider-2", "enabled": True},
        ],
    )
    def _validate_provider(_db, *, config, provider_instance_id):
        del config
        if provider_instance_id == "provider-1":
            return {
                "provider": {"id": provider_instance_id, "slug": "provider-1"},
                "validation": {
                    "health": {"reachable": False, "status_code": 503},
                    "models_reachable": False,
                },
            }
        if provider_instance_id == "provider-embeddings":
            return {
                "provider": {"id": provider_instance_id, "slug": "provider-embeddings"},
                "validation": {
                    "health": {"reachable": True, "status_code": 200},
                    "embeddings_reachable": True,
                },
            }
        return {
            "provider": {"id": provider_instance_id, "slug": "provider-2"},
            "validation": {"health": {"reachable": True, "status_code": 200}},
        }

    monkeypatch.setattr(platform_service, "validate_provider", _validate_provider)

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        platform_service.activate_deployment_profile(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            deployment_profile_id="deployment-1",
            activated_by_user_id=1,
        )

    assert exc_info.value.code == "deployment_profile_validation_failed"
    assert exc_info.value.details["providers"][0]["provider"]["slug"] == "provider-1"


def test_delete_provider_rejects_bound_instances(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: {"id": provider_instance_id, "slug": "provider-a"},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "count_deployment_bindings_for_provider",
        lambda _db, *, provider_instance_id: 2,
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        platform_service.delete_provider("ignored", config=object(), provider_instance_id="provider-1")  # type: ignore[arg-type]

    assert exc_info.value.code == "provider_instance_in_use"
    assert exc_info.value.details["binding_count"] == 2


def test_serialize_provider_row_exposes_secret_refs_separately():
    payload = platform_service._serialize_provider_row(  # type: ignore[attr-defined]
        {
            "id": "provider-1",
            "slug": "provider-a",
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
            "adapter_kind": "openai_compatible_llm",
            "display_name": "Provider A",
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {
                "chat_completion_path": "/v1/chat/completions",
                "secret_refs": {"api_key": "env://API_KEY"},
            },
        }
    )

    assert payload["config"] == {"chat_completion_path": "/v1/chat/completions"}
    assert payload["secret_refs"] == {"api_key": "env://API_KEY"}


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


def test_openai_adapter_uses_models_endpoint_for_health_when_no_healthcheck(monkeypatch: pytest.MonkeyPatch):
    seen_urls: list[str] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del payload, headers, timeout_seconds
        seen_urls.append(url)
        return {"data": [{"id": "local-llama-cpp-default"}]}, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.OpenAICompatibleLlmAdapter(
        platform_service.ProviderBinding(
            capability_key="llm_inference",
            provider_instance_id="provider-2",
            provider_slug="llama-cpp-local",
            provider_key="llama_cpp_local",
            provider_display_name="llama.cpp local",
            provider_description="desc",
            endpoint_url="http://llama_cpp:8080",
            healthcheck_url=None,
            enabled=True,
            adapter_kind="openai_compatible_llm",
            config={"models_path": "/v1/models"},
            binding_config={},
            deployment_profile_id="deployment-2",
            deployment_profile_slug="local-llama-cpp",
            deployment_profile_display_name="Local llama.cpp",
        )
    )

    health = adapter.health()

    assert health["reachable"] is True
    assert seen_urls == ["http://llama_cpp:8080/v1/models"]


def test_validate_provider_supports_embeddings_capability(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: {
            "id": provider_instance_id,
            "slug": "vllm-embeddings-local",
            "provider_key": "vllm_embeddings_local",
            "capability_key": "embeddings",
            "adapter_kind": "openai_compatible_embeddings",
            "display_name": "vLLM embeddings local",
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
        },
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda _db, config, provider_instance_id=None: type(
            "FakeEmbeddingsAdapter",
            (),
            {
                "binding": platform_service.ProviderBinding(
                    capability_key="embeddings",
                    provider_instance_id="provider-embeddings",
                    provider_slug="vllm-embeddings-local",
                    provider_key="vllm_embeddings_local",
                    provider_display_name="vLLM embeddings local",
                    provider_description="desc",
                    endpoint_url="http://llm:8000",
                    healthcheck_url="http://llm:8000/health",
                    enabled=True,
                    adapter_kind="openai_compatible_embeddings",
                    config={"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
                    binding_config={},
                    deployment_profile_id="deployment-1",
                    deployment_profile_slug="local-default",
                    deployment_profile_display_name="Local Default",
                ),
                "health": lambda self: {"reachable": True, "status_code": 200},
                "embed_texts": lambda self, *, texts: (
                    {"embeddings": [[0.1, 0.2, 0.3]], "embedding_dimension": 3},
                    200,
                ),
            },
        )(),
    )

    payload = platform_service.validate_provider("ignored", config=object(), provider_instance_id="provider-embeddings")  # type: ignore[arg-type]

    assert payload["validation"] == {
        "health": {"reachable": True, "status_code": 200},
        "embeddings_reachable": True,
        "embeddings_status_code": 200,
        "embedding_dimension": 3,
    }


def test_openai_adapter_normalizes_openai_chat_payloads(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "llama.cpp says hi",
                    }
                }
            ]
        }, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.OpenAICompatibleLlmAdapter(
        platform_service.ProviderBinding(
            capability_key="llm_inference",
            provider_instance_id="provider-2",
            provider_slug="llama-cpp-local",
            provider_key="llama_cpp_local",
            provider_display_name="llama.cpp local",
            provider_description="desc",
            endpoint_url="http://llama_cpp:8080",
            healthcheck_url=None,
            enabled=True,
            adapter_kind="openai_compatible_llm",
            config={
                "chat_completion_path": "/v1/chat/completions",
                "request_format": "openai_chat",
                "forced_model_id": "local-llama-cpp-default",
            },
            binding_config={},
            deployment_profile_id="deployment-2",
            deployment_profile_slug="local-llama-cpp",
            deployment_profile_display_name="Local llama.cpp",
        )
    )

    payload, status_code = adapter.chat_completion(
        model="allowed-model",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        max_tokens=64,
        temperature=0.1,
        allow_local_fallback=True,
    )

    assert status_code == 200
    assert seen_payloads == [
        {
            "model": "local-llama-cpp-default",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 64,
            "temperature": 0.1,
        }
    ]
    assert payload == {
        "choices": [{"message": {"role": "assistant", "content": "llama.cpp says hi"}}],
        "output": [{"role": "assistant", "content": [{"type": "text", "text": "llama.cpp says hi"}]}],
    }


def test_ensure_platform_bootstrap_state_seeds_llama_cpp_profile_when_configured(monkeypatch: pytest.MonkeyPatch):
    created_profiles: list[str] = []
    binding_calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})

    def _ensure_provider_instance(_db, **kwargs):
        return {"id": f"{kwargs['slug']}-id"}

    def _ensure_deployment_profile(_db, *, slug, **kwargs):
        created_profiles.append(slug)
        return {"id": f"{slug}-id"}

    def _upsert_deployment_binding(_db, *, deployment_profile_id, capability_key, provider_instance_id, binding_config):
        del binding_config
        binding_calls.append((deployment_profile_id, capability_key, provider_instance_id))
        return {}

    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", _ensure_provider_instance)
    monkeypatch.setattr(platform_service.platform_repo, "ensure_deployment_profile", _ensure_deployment_profile)
    monkeypatch.setattr(platform_service.platform_repo, "upsert_deployment_binding", _upsert_deployment_binding)
    monkeypatch.setattr(platform_service.platform_repo, "get_active_deployment", lambda _db: {"deployment_profile_id": "active"})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *args, **kwargs: {})

    config = SimpleNamespace(
        llm_url="http://llm:8000",
        llm_runtime_url="http://llm_runtime:8000",
        weaviate_url="http://weaviate:8080",
        llama_cpp_url="http://llama_cpp:8080",
        qdrant_url="",
    )

    platform_service.ensure_platform_bootstrap_state("ignored", config)  # type: ignore[arg-type]

    assert created_profiles == ["local-default", "local-llama-cpp"]
    assert ("local-llama-cpp-id", "llm_inference", "llama-cpp-local-id") in binding_calls
    assert ("local-llama-cpp-id", "embeddings", "vllm-embeddings-local-id") in binding_calls
    assert ("local-llama-cpp-id", "vector_store", "weaviate-local-id") in binding_calls


def test_ensure_platform_bootstrap_state_skips_llama_cpp_profile_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    created_profiles: list[str] = []

    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", lambda _db, **kwargs: {"id": f"{kwargs['slug']}-id"})
    monkeypatch.setattr(
        platform_service.platform_repo,
        "ensure_deployment_profile",
        lambda _db, *, slug, **kwargs: created_profiles.append(slug) or {"id": f"{slug}-id"},
    )
    monkeypatch.setattr(platform_service.platform_repo, "upsert_deployment_binding", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "get_active_deployment", lambda _db: {"deployment_profile_id": "active"})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *args, **kwargs: {})

    config = SimpleNamespace(
        llm_url="http://llm:8000",
        llm_runtime_url="http://llm_runtime:8000",
        weaviate_url="http://weaviate:8080",
        llama_cpp_url="",
        qdrant_url="",
    )

    platform_service.ensure_platform_bootstrap_state("ignored", config)  # type: ignore[arg-type]

    assert created_profiles == ["local-default"]


def test_ensure_platform_bootstrap_state_seeds_qdrant_profile_when_configured(monkeypatch: pytest.MonkeyPatch):
    created_profiles: list[str] = []
    binding_calls: list[tuple[str, str, str]] = []

    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", lambda _db, **kwargs: {"id": f"{kwargs['slug']}-id"})
    monkeypatch.setattr(
        platform_service.platform_repo,
        "ensure_deployment_profile",
        lambda _db, *, slug, **kwargs: created_profiles.append(slug) or {"id": f"{slug}-id"},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "upsert_deployment_binding",
        lambda _db, *, deployment_profile_id, capability_key, provider_instance_id, binding_config: (
            binding_calls.append((deployment_profile_id, capability_key, provider_instance_id)) or {}
        ),
    )
    monkeypatch.setattr(platform_service.platform_repo, "get_active_deployment", lambda _db: {"deployment_profile_id": "active"})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *args, **kwargs: {})

    config = SimpleNamespace(
        llm_url="http://llm:8000",
        llm_runtime_url="http://llm_runtime:8000",
        weaviate_url="http://weaviate:8080",
        llama_cpp_url="",
        qdrant_url="http://qdrant:6333",
    )

    platform_service.ensure_platform_bootstrap_state("ignored", config)  # type: ignore[arg-type]

    assert created_profiles == ["local-default", "local-qdrant"]
    assert ("local-qdrant-id", "llm_inference", "vllm-local-gateway-id") in binding_calls
    assert ("local-qdrant-id", "embeddings", "vllm-embeddings-local-id") in binding_calls
    assert ("local-qdrant-id", "vector_store", "qdrant-local-id") in binding_calls


def test_resolve_vector_store_adapter_supports_qdrant(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_active_binding_for_capability",
        lambda _db, *, capability_key: {
            "capability_key": capability_key,
            "provider_instance_id": "provider-2",
            "provider_slug": "qdrant-local",
            "provider_key": "qdrant_local",
            "provider_display_name": "Qdrant local",
            "provider_description": "desc",
            "endpoint_url": "http://qdrant:6333",
            "healthcheck_url": "http://qdrant:6333/healthz",
            "enabled": True,
            "config_json": {},
            "binding_config": {},
            "adapter_kind": "qdrant_http",
            "deployment_profile_id": "deployment-2",
            "deployment_profile_slug": "local-qdrant",
            "deployment_profile_display_name": "Local Qdrant",
        },
    )

    adapter = platform_service.resolve_vector_store_adapter("ignored", object())  # type: ignore[arg-type]

    assert isinstance(adapter, platform_adapters.QdrantVectorStoreAdapter)
    assert adapter.binding.provider_slug == "qdrant-local"


@pytest.mark.parametrize(
    ("llm_provider_key", "deployment_slug", "vector_provider_key", "vector_adapter_kind", "vector_endpoint_url"),
    [
        ("vllm_local", "local-default", "weaviate_local", "weaviate_http", "http://weaviate:8080"),
        ("llama_cpp_local", "local-llama-cpp", "weaviate_local", "weaviate_http", "http://weaviate:8080"),
        ("vllm_local", "local-qdrant", "qdrant_local", "qdrant_http", "http://qdrant:6333"),
    ],
)
def test_get_active_platform_runtime_uses_current_active_bindings(
    monkeypatch: pytest.MonkeyPatch,
    llm_provider_key: str,
    deployment_slug: str,
    vector_provider_key: str,
    vector_adapter_kind: str,
    vector_endpoint_url: str,
):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)

    def _active_binding(_db, *, capability_key):
        if capability_key == "llm_inference":
            return {
                "capability_key": "llm_inference",
                "provider_instance_id": "provider-1",
                "provider_slug": "llm-provider",
                "provider_key": llm_provider_key,
                "provider_display_name": "LLM Provider",
                "provider_description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {"chat_completion_path": "/v1/chat/completions"},
                "binding_config": {},
                "adapter_kind": "openai_compatible_llm",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": deployment_slug,
                "deployment_profile_display_name": "Runtime Deployment",
            }
        if capability_key == "embeddings":
            return {
                "capability_key": "embeddings",
                "provider_instance_id": "provider-embeddings",
                "provider_slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "provider_display_name": "vLLM embeddings local",
                "provider_description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
                "binding_config": {},
                "adapter_kind": "openai_compatible_embeddings",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": deployment_slug,
                "deployment_profile_display_name": "Runtime Deployment",
            }
        return {
            "capability_key": "vector_store",
            "provider_instance_id": "provider-2",
            "provider_slug": "weaviate-local" if vector_provider_key == "weaviate_local" else "qdrant-local",
            "provider_key": vector_provider_key,
            "provider_display_name": "Weaviate local" if vector_provider_key == "weaviate_local" else "Qdrant local",
            "provider_description": "desc",
            "endpoint_url": vector_endpoint_url,
            "healthcheck_url": (
                "http://weaviate:8080/v1/.well-known/ready"
                if vector_provider_key == "weaviate_local"
                else "http://qdrant:6333/healthz"
            ),
            "enabled": True,
            "config_json": {},
            "binding_config": {},
            "adapter_kind": vector_adapter_kind,
            "deployment_profile_id": "deployment-1",
            "deployment_profile_slug": deployment_slug,
            "deployment_profile_display_name": "Runtime Deployment",
        }

    monkeypatch.setattr(platform_service.platform_repo, "get_active_binding_for_capability", _active_binding)

    payload = platform_service.get_active_platform_runtime("ignored", object())  # type: ignore[arg-type]

    assert payload == {
        "deployment_profile": {
            "id": "deployment-1",
            "slug": deployment_slug,
            "display_name": "Runtime Deployment",
        },
        "capabilities": {
            "llm_inference": {
                "id": "provider-1",
                "slug": "llm-provider",
                "provider_key": llm_provider_key,
                "display_name": "LLM Provider",
                "description": "desc",
                "adapter_kind": "openai_compatible_llm",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config": {"chat_completion_path": "/v1/chat/completions"},
                "binding_config": {},
            },
            "embeddings": {
                "id": "provider-embeddings",
                "slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "display_name": "vLLM embeddings local",
                "description": "desc",
                "adapter_kind": "openai_compatible_embeddings",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config": {"embeddings_path": "/v1/embeddings", "forced_model_id": "local-vllm-embeddings-default"},
                "binding_config": {},
            },
            "vector_store": {
                "id": "provider-2",
                "slug": "weaviate-local" if vector_provider_key == "weaviate_local" else "qdrant-local",
                "provider_key": vector_provider_key,
                "display_name": "Weaviate local" if vector_provider_key == "weaviate_local" else "Qdrant local",
                "description": "desc",
                "adapter_kind": vector_adapter_kind,
                "endpoint_url": vector_endpoint_url,
                "healthcheck_url": (
                    "http://weaviate:8080/v1/.well-known/ready"
                    if vector_provider_key == "weaviate_local"
                    else "http://qdrant:6333/healthz"
                ),
                "enabled": True,
                "config": {},
                "binding_config": {},
            },
        },
    }
