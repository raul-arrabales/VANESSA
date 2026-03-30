from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import platform_adapters, platform_bootstrap, platform_service  # noqa: E402
from app.services.platform_types import DeploymentBindingInput, PlatformControlPlaneError  # noqa: E402


def _db_shaped_embeddings_model_row() -> dict[str, object]:
    return {
        "id": 5,
        "model_id": "sentence-transformers--all-MiniLM-L6-v2",
        "name": "MiniLM Embeddings",
        "provider": "huggingface",
        "provider_model_id": "local-vllm-embeddings-default",
        "source_id": "hf/sentence-transformers/all-MiniLM-L6-v2",
        "backend_kind": "local",
        "availability": "offline_ready",
        "task_key": "embeddings",
        "lifecycle_state": "active",
        "is_validation_current": True,
        "last_validation_status": "success",
        "local_path": "/models/all-MiniLM-L6-v2",
    }


def _provider_rows_by_id() -> dict[str, dict[str, object]]:
    return {
        "provider-llm": {
            "id": "provider-llm",
            "slug": "vllm-local-gateway",
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
            "display_name": "vLLM local gateway",
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "adapter_kind": "openai_compatible_llm",
        },
        "provider-embeddings": {
            "id": "provider-embeddings",
            "slug": "vllm-embeddings-local",
            "provider_key": "vllm_embeddings_local",
            "capability_key": "embeddings",
            "display_name": "vLLM embeddings local",
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "adapter_kind": "openai_compatible_embeddings",
        },
        "provider-vector": {
            "id": "provider-vector",
            "slug": "weaviate-local",
            "provider_key": "weaviate_local",
            "capability_key": "vector_store",
            "display_name": "Weaviate local",
            "description": "desc",
            "endpoint_url": "http://weaviate:8080",
            "healthcheck_url": "http://weaviate:8080/v1/.well-known/ready",
            "enabled": True,
            "adapter_kind": "weaviate_http",
        },
    }


def _resolved_binding_row(
    providers_by_id: dict[str, dict[str, object]],
    binding: dict[str, object],
) -> dict[str, object]:
    provider = providers_by_id[str(binding["provider_instance_id"])]
    resources = [dict(item) for item in binding.get("resources") or [] if isinstance(item, dict)]
    default_resource_id = str(binding.get("default_resource_id") or "").strip() or None
    return {
        "id": f"{binding['capability_key']}-binding-id",
        "capability_key": binding["capability_key"],
        "provider_instance_id": binding["provider_instance_id"],
        "provider_slug": provider["slug"],
        "provider_key": provider["provider_key"],
        "provider_display_name": provider["display_name"],
        "provider_description": provider["description"],
        "endpoint_url": provider["endpoint_url"],
        "healthcheck_url": provider["healthcheck_url"],
        "enabled": provider["enabled"],
        "adapter_kind": provider["adapter_kind"],
        "binding_config": dict(binding.get("binding_config") or {}),
        "resource_policy": dict(binding.get("resource_policy") or {}),
        "resources": resources,
        "default_resource_id": default_resource_id,
        "default_resource": next(
            (dict(item) for item in resources if str(item.get("id") or "").strip() == default_resource_id),
            None,
        ),
    }


def _deployment_payload_with_embeddings_resource(model_id: str) -> dict[str, object]:
    return {
        "slug": "profile-a",
        "display_name": "Profile A",
        "description": "",
        "bindings": [
            {"capability": "llm_inference", "provider_id": "provider-llm"},
            {
                "capability": "embeddings",
                "provider_id": "provider-embeddings",
                "resources": [
                    {
                        "id": model_id,
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": model_id,
                        "display_name": "MiniLM Embeddings",
                        "metadata": {},
                    }
                ],
                "default_resource_id": model_id,
            },
            {
                "capability": "vector_store",
                "provider_id": "provider-vector",
                "resource_policy": {"selection_mode": "explicit"},
            },
        ],
    }


def test_build_model_binding_resource_uses_public_model_id():
    resource = platform_service._build_model_binding_resource(  # type: ignore[attr-defined]
        _db_shaped_embeddings_model_row(),
        provider_resource_id="local-vllm-embeddings-default",
    )

    assert resource["id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert resource["managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"


def test_runtime_identifier_for_resource_ignores_string_none_provider_resource_id():
    runtime_identifier = platform_service._runtime_identifier_for_resource(  # type: ignore[attr-defined]
        {
            "provider_resource_id": "None",
            "metadata": {"local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2"},
        }
    )

    assert runtime_identifier == "/models/llm/sentence-transformers--all-MiniLM-L6-v2"


def test_default_resource_runtime_identifier_ignores_string_none_provider_resource_id():
    binding = platform_service.ProviderBinding(
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
        config={"embeddings_path": "/v1/embeddings"},
        binding_config={},
        deployment_profile_id="deployment-1",
        deployment_profile_slug="local-default",
        deployment_profile_display_name="Local Default",
        default_resource={
            "provider_resource_id": "None",
            "metadata": {"local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2"},
        },
    )

    assert (
        platform_adapters._default_resource_runtime_identifier(binding)
        == "/models/llm/sentence-transformers--all-MiniLM-L6-v2"
    )


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
    monkeypatch.setattr(platform_service, "_known_capability_keys", lambda _db: {"llm_inference", "embeddings", "vector_store"})
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


def test_create_deployment_profile_allows_empty_resources_for_required_bindings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(platform_service, "_known_capability_keys", lambda _db: {"llm_inference", "embeddings", "vector_store"})
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_id: {
            "id": provider_id,
            "provider_key": "weaviate_local" if provider_id == "provider-vector" else "vllm_embeddings_local",
            "capability_key": "vector_store" if provider_id == "provider-vector" else ("llm_inference" if provider_id == "provider-llm" else "embeddings"),
        },
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "create_deployment_profile",
        lambda _db, **kwargs: {
            "id": "deployment-1",
            "slug": kwargs["slug"],
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "is_active": False,
        },
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [
            {
                "capability_key": "llm_inference",
                "provider_instance_id": "provider-llm",
                "provider_slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "provider_display_name": "vLLM local gateway",
                "endpoint_url": "http://llm:8000",
                "enabled": True,
                "adapter_kind": "openai_compatible_llm",
                "resources": [],
                "default_resource_id": None,
                "resource_policy": {},
            },
            {
                "capability_key": "embeddings",
                "provider_instance_id": "provider-embeddings",
                "provider_slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "provider_display_name": "vLLM embeddings local",
                "endpoint_url": "http://llm:8000",
                "enabled": True,
                "adapter_kind": "openai_compatible_embeddings",
                "resources": [],
                "default_resource_id": None,
                "resource_policy": {},
            },
            {
                "capability_key": "vector_store",
                "provider_instance_id": "provider-vector",
                "provider_slug": "weaviate-local",
                "provider_key": "weaviate_local",
                "provider_display_name": "Weaviate local",
                "endpoint_url": "http://weaviate:8080",
                "enabled": True,
                "adapter_kind": "weaviate_http",
                "resources": [],
                "default_resource_id": None,
                "resource_policy": {"selection_mode": "explicit"},
            },
        ],
    )

    deployment = platform_service.create_deployment_profile(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        payload={
            "slug": "profile-a",
            "display_name": "Profile A",
            "bindings": [
                {"capability": "llm_inference", "provider_id": "provider-llm"},
                {"capability": "embeddings", "provider_id": "provider-embeddings"},
                {"capability": "vector_store", "provider_id": "provider-vector", "resource_policy": {"selection_mode": "explicit"}},
            ],
        },
        created_by_user_id=1,
    )

    assert deployment["configuration_status"]["is_ready"] is False
    assert deployment["configuration_status"]["incomplete_capabilities"] == ["embeddings", "llm_inference", "vector_store"]


@pytest.mark.parametrize("save_mode", ["create", "update", "upsert"])
def test_model_bearing_deployment_save_paths_use_public_model_id(
    monkeypatch: pytest.MonkeyPatch,
    save_mode: str,
):
    model_row = _db_shaped_embeddings_model_row()
    model_id = str(model_row["model_id"])
    providers_by_id = _provider_rows_by_id()
    stored_bindings: list[dict[str, object]] = [
        _resolved_binding_row(
            providers_by_id,
            {
                "capability_key": "llm_inference",
                "provider_instance_id": "provider-llm",
                "resources": [],
                "default_resource_id": None,
                "binding_config": {},
                "resource_policy": {},
            },
        ),
        _resolved_binding_row(
            providers_by_id,
            {
                "capability_key": "vector_store",
                "provider_instance_id": "provider-vector",
                "resources": [],
                "default_resource_id": None,
                "binding_config": {},
                "resource_policy": {"selection_mode": "explicit"},
            },
        ),
    ]
    captured: dict[str, object] = {}

    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service,
        "_known_capability_keys",
        lambda _db: {"llm_inference", "embeddings", "vector_store"},
    )
    monkeypatch.setattr(
        platform_service._platform_bindings_module,  # type: ignore[attr-defined]
        "get_model_by_id",
        lambda _db, managed_model_id: dict(model_row) if managed_model_id == model_id else None,
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_id: dict(providers_by_id[provider_id]),
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [dict(item) for item in stored_bindings],
    )

    def _set_stored_bindings_from_resolved(bindings: list[dict[str, object]]) -> None:
        stored_bindings[:] = [_resolved_binding_row(providers_by_id, binding) for binding in bindings]

    if save_mode == "create":
        def _create_deployment_profile(_db, **kwargs):
            captured["bindings"] = kwargs["bindings"]
            _set_stored_bindings_from_resolved(kwargs["bindings"])
            return {
                "id": "deployment-1",
                "slug": kwargs["slug"],
                "display_name": kwargs["display_name"],
                "description": kwargs["description"],
                "is_active": False,
            }

        monkeypatch.setattr(platform_service.platform_repo, "create_deployment_profile", _create_deployment_profile)
        deployment = platform_service.create_deployment_profile(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            payload=_deployment_payload_with_embeddings_resource(model_id),
            created_by_user_id=1,
        )
    elif save_mode == "update":
        monkeypatch.setattr(
            platform_service.platform_repo,
            "get_deployment_profile",
            lambda _db, deployment_profile_id: {
                "id": deployment_profile_id,
                "slug": "profile-a",
                "display_name": "Profile A",
                "description": "",
                "is_active": False,
            },
        )

        def _update_deployment_profile(_db, **kwargs):
            captured["bindings"] = kwargs["bindings"]
            _set_stored_bindings_from_resolved(kwargs["bindings"])
            return {
                "id": kwargs["deployment_profile_id"],
                "slug": kwargs["slug"],
                "display_name": kwargs["display_name"],
                "description": kwargs["description"],
                "is_active": False,
            }

        monkeypatch.setattr(platform_service.platform_repo, "update_deployment_profile", _update_deployment_profile)
        deployment = platform_service.update_deployment_profile(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            deployment_profile_id="deployment-1",
            payload=_deployment_payload_with_embeddings_resource(model_id),
            updated_by_user_id=1,
        )
    else:
        monkeypatch.setattr(
            platform_service.platform_repo,
            "get_deployment_profile",
            lambda _db, deployment_profile_id: {
                "id": deployment_profile_id,
                "slug": "profile-a",
                "display_name": "Profile A",
                "description": "",
                "is_active": False,
            },
        )

        def _upsert_deployment_binding(
            _db,
            *,
            deployment_profile_id,
            capability_key,
            provider_instance_id,
            resources,
            default_resource_id,
            binding_config,
            resource_policy,
        ):
            captured["resources"] = [dict(item) for item in resources]
            captured["default_resource_id"] = default_resource_id
            embeddings_binding = _resolved_binding_row(
                providers_by_id,
                {
                    "capability_key": capability_key,
                    "provider_instance_id": provider_instance_id,
                    "resources": [dict(item) for item in resources],
                    "default_resource_id": default_resource_id,
                    "binding_config": dict(binding_config),
                    "resource_policy": dict(resource_policy),
                },
            )
            stored_bindings[:] = [
                item for item in stored_bindings if str(item.get("capability_key")) != capability_key
            ] + [embeddings_binding]
            return dict(embeddings_binding)

        monkeypatch.setattr(platform_service.platform_repo, "upsert_deployment_binding", _upsert_deployment_binding)
        monkeypatch.setattr(
            platform_service.platform_repo,
            "update_deployment_profile_identity",
            lambda _db, **kwargs: {
                "id": kwargs["deployment_profile_id"],
                "slug": kwargs["slug"],
                "display_name": kwargs["display_name"],
                "description": kwargs["description"],
                "is_active": False,
            },
        )
        deployment = platform_service.upsert_deployment_profile_binding(
            "ignored",
            config=object(),  # type: ignore[arg-type]
            deployment_profile_id="deployment-1",
            capability_key="embeddings",
            payload={
                "provider_id": "provider-embeddings",
                "resources": [
                    {
                        "id": model_id,
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": model_id,
                        "display_name": "MiniLM Embeddings",
                        "metadata": {},
                    }
                ],
                "default_resource_id": model_id,
            },
            updated_by_user_id=1,
        )

    binding = next(item for item in deployment["bindings"] if item["capability"] == "embeddings")
    assert binding["default_resource_id"] == model_id
    assert binding["resources"][0]["id"] == model_id
    assert binding["resources"][0]["managed_model_id"] == model_id

    if save_mode == "upsert":
        assert captured["default_resource_id"] == model_id
        assert captured["resources"][0]["id"] == model_id
        assert captured["resources"][0]["managed_model_id"] == model_id
    else:
        embeddings_binding = next(
            item for item in captured["bindings"] if str(item["capability_key"]) == "embeddings"
        )
        assert embeddings_binding["default_resource_id"] == model_id
        assert embeddings_binding["resources"][0]["id"] == model_id
        assert embeddings_binding["resources"][0]["managed_model_id"] == model_id


def test_resolve_deployment_bindings_keeps_cross_capability_kb_checks_out_of_save_time(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(platform_service, "_known_capability_keys", lambda _db: {"embeddings", "vector_store"})
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_id: {
            "id": provider_id,
            "provider_key": "vllm_embeddings_local" if provider_id == "provider-embeddings" else "weaviate_local",
            "capability_key": "embeddings" if provider_id == "provider-embeddings" else "vector_store",
        },
    )

    seen_resources: list[tuple[str, list[dict[str, object]]]] = []

    def _validate_binding_resources(
        _database_url,
        *,
        provider_row,
        capability_key,
        resources,
        default_resource_id,
        resource_policy,
    ):
        seen_resources.append((capability_key, [dict(item) for item in resources]))
        return {
            "resources": [dict(item) for item in resources],
            "default_resource_id": default_resource_id,
        }

    monkeypatch.setattr(
        platform_service._platform_bindings_module,  # type: ignore[attr-defined]
        "_validate_binding_resources",
        _validate_binding_resources,
    )

    resolved = platform_service._resolve_deployment_bindings(  # type: ignore[attr-defined]
        "ignored",
        [
            DeploymentBindingInput(
                capability_key="embeddings",
                provider_instance_id="provider-embeddings",
                resources=[
                    {
                        "id": "embed-model",
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": "embed-model",
                    }
                ],
                default_resource_id="embed-model",
            ),
            DeploymentBindingInput(
                capability_key="vector_store",
                provider_instance_id="provider-vector",
                resources=[
                    {
                        "id": "kb-primary",
                        "resource_kind": "knowledge_base",
                        "ref_type": "knowledge_base",
                        "knowledge_base_id": "kb-primary",
                    }
                ],
                default_resource_id="kb-primary",
            ),
        ],
    )

    assert [item["capability_key"] for item in resolved] == ["embeddings", "vector_store"]
    assert seen_resources == [
        (
            "embeddings",
            [
                {
                    "id": "embed-model",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "embed-model",
                }
            ],
        ),
        (
            "vector_store",
            [
                {
                    "id": "kb-primary",
                    "resource_kind": "knowledge_base",
                    "ref_type": "knowledge_base",
                    "knowledge_base_id": "kb-primary",
                }
            ],
        ),
    ]


def test_activate_deployment_profile_allows_incomplete_required_capabilities(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_deployment_profile",
        lambda _db, deployment_profile_id: {
            "id": deployment_profile_id,
            "slug": "profile-a",
            "display_name": "Profile A",
            "description": "",
            "is_active": True,
        },
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [
            {
                "capability_key": "llm_inference",
                "provider_instance_id": "provider-1",
                "provider_slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "provider_display_name": "vLLM local gateway",
                "endpoint_url": "http://llm:8000",
                "enabled": True,
                "adapter_kind": "openai_compatible_llm",
                "resources": [],
                "default_resource_id": None,
                "resource_policy": {},
            },
        ],
    )
    monkeypatch.setattr(platform_service, "_validate_provider_binding", lambda _binding: {"health": {"reachable": True, "status_code": 200}})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *_args, **_kwargs: None)

    deployment = platform_service.activate_deployment_profile(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        deployment_profile_id="deployment-1",
        activated_by_user_id=1,
    )

    assert deployment["configuration_status"]["is_ready"] is False
    assert deployment["configuration_status"]["incomplete_capabilities"] == ["embeddings", "llm_inference", "vector_store"]


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
    def _validate_binding(binding):
        if binding.provider_instance_id == "provider-1":
            return {
                "health": {"reachable": False, "status_code": 503},
                "models_reachable": False,
            }
        if binding.provider_instance_id == "provider-embeddings":
            return {
                "health": {"reachable": True, "status_code": 200},
                "embeddings_reachable": True,
            }
        return {"health": {"reachable": True, "status_code": 200}}

    monkeypatch.setattr(platform_service, "_validate_provider_binding", _validate_binding)

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


def test_validate_non_model_resources_accepts_ready_active_knowledge_base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_service.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "slug": "product-docs",
            "display_name": "Product Docs",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": "ready",
            "document_count": 4,
        },
    )

    payload = platform_service._validate_non_model_resources(  # type: ignore[attr-defined]
        database_url="ignored",
        provider_row={"id": "provider-2", "provider_key": "weaviate_local"},
        capability_key="vector_store",
        resources=[{"id": "kb-primary", "ref_type": "knowledge_base"}],
        default_resource_id="kb-primary",
        resource_policy={"selection_mode": "explicit"},
    )

    assert payload["default_resource_id"] == "kb-primary"
    assert payload["resources"] == [
        {
            "id": "kb-primary",
            "resource_kind": "knowledge_base",
            "ref_type": "knowledge_base",
            "knowledge_base_id": "kb-primary",
            "provider_resource_id": "kb_product_docs",
            "display_name": "Product Docs",
            "metadata": {
                "slug": "product-docs",
                "index_name": "kb_product_docs",
                "backing_provider_instance_id": "provider-2",
                "backing_provider_key": "weaviate_local",
                "lifecycle_state": "active",
                "sync_status": "ready",
                "document_count": 4,
            },
        }
    ]


def test_validate_non_model_resources_rejects_provider_instance_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_service.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "slug": "product-docs",
            "display_name": "Product Docs",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "lifecycle_state": "active",
            "sync_status": "ready",
            "document_count": 4,
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        platform_service._validate_non_model_resources(  # type: ignore[attr-defined]
            database_url="ignored",
            provider_row={"id": "provider-9", "provider_key": "qdrant_local"},
            capability_key="vector_store",
            resources=[{"id": "kb-primary", "ref_type": "knowledge_base"}],
            default_resource_id="kb-primary",
            resource_policy={"selection_mode": "explicit"},
        )

    assert exc_info.value.code == "resource_provider_mismatch"
    assert exc_info.value.details == {
        "knowledge_base_id": "kb-primary",
        "knowledge_base_provider_instance_id": "provider-2",
        "provider_instance_id": "provider-9",
        "knowledge_base_provider_key": "weaviate_local",
        "provider_key": "qdrant_local",
    }


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


def test_local_slot_payload_from_config_treats_string_none_values_as_missing():
    payload = platform_service._local_slot_payload_from_config(  # type: ignore[attr-defined]
        {
            "loaded_managed_model_id": "None",
            "loaded_managed_model_name": "None",
            "loaded_runtime_model_id": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
            "loaded_local_path": "null",
            "loaded_source_id": "None",
            "load_state": "loaded",
            "load_error": "None",
        }
    )

    assert payload["loaded_managed_model_id"] is None
    assert payload["loaded_managed_model_name"] is None
    assert payload["loaded_runtime_model_id"] == "/models/llm/Qwen--Qwen2.5-0.5B-Instruct"
    assert payload["loaded_local_path"] is None
    assert payload["loaded_source_id"] is None
    assert payload["load_error"] is None


def test_local_slot_runtime_state_backfills_missing_managed_model_metadata():
    payload = platform_service._local_slot_with_runtime_state(  # type: ignore[attr-defined]
        {
            "loaded_managed_model_id": None,
            "loaded_managed_model_name": None,
            "loaded_runtime_model_id": None,
            "loaded_local_path": None,
            "load_state": "reconciling",
            "load_error": None,
        },
        {
            "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "display_name": "sentence-transformers/all-MiniLM-L6-v2",
            "runtime_model_id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "load_state": "loaded",
            "last_error": None,
        },
        200,
    )

    assert payload["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert payload["loaded_managed_model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert payload["loaded_runtime_model_id"] == "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2"
    assert payload["load_state"] == "loaded"


def test_local_slot_runtime_state_preserves_persisted_managed_model_metadata_when_runtime_omits_it():
    payload = platform_service._local_slot_with_runtime_state(  # type: ignore[attr-defined]
        {
            "loaded_managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "loaded_managed_model_name": "Persisted MiniLM",
            "loaded_runtime_model_id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
            "loaded_local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "load_state": "loading",
            "load_error": None,
        },
        {
            "managed_model_id": None,
            "display_name": None,
            "runtime_model_id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "load_state": "loaded",
            "last_error": None,
        },
        200,
    )

    assert payload["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert payload["loaded_managed_model_name"] == "Persisted MiniLM"
    assert payload["load_state"] == "loaded"


def test_effective_local_slot_only_marks_loaded_when_runtime_inventory_advertises_loaded_model(monkeypatch: pytest.MonkeyPatch):
    provider_row = {
        "id": "provider-embeddings",
        "slug": "vllm-embeddings-local",
        "provider_key": "vllm_embeddings_local",
        "capability_key": "embeddings",
        "adapter_kind": "openai_compatible_embeddings",
        "display_name": "vLLM embeddings local",
        "description": "desc",
        "endpoint_url": "http://llm:8000",
        "healthcheck_url": "http://llm:8000/health",
        "enabled": True,
        "config_json": {
            "loaded_runtime_model_id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
            "load_state": "reconciling",
        },
    }
    monkeypatch.setattr(
        platform_service,
        "_runtime_admin_state",
        lambda _row: (
            {
                "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
                "display_name": "sentence-transformers/all-MiniLM-L6-v2",
                "runtime_model_id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2",
                "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
                "load_state": "loaded",
                "last_error": None,
            },
            200,
        ),
    )
    monkeypatch.setattr(platform_service, "_provider_runtime_inventory", lambda _row: ([], 200))

    payload = platform_service._effective_local_slot(provider_row)  # type: ignore[attr-defined]

    assert payload["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert payload["loaded_managed_model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert payload["load_state"] == "reconciling"

    monkeypatch.setattr(
        platform_service,
        "_provider_runtime_inventory",
        lambda _row: ([{"id": "/models/embeddings/sentence-transformers--all-MiniLM-L6-v2"}], 200),
    )

    loaded_payload = platform_service._effective_local_slot(provider_row)  # type: ignore[attr-defined]

    assert loaded_payload["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert loaded_payload["loaded_managed_model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert loaded_payload["load_state"] == "loaded"


def test_assign_provider_loaded_model_persists_local_slot(monkeypatch: pytest.MonkeyPatch):
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
            "config_json": {"models_path": "/v1/models"},
        },
    )
    monkeypatch.setattr(
        platform_service,
        "get_model_by_id",
        lambda _db, model_id: {
            "id": model_id,
            "model_id": model_id,
            "name": "MiniLM",
            "task_key": "embeddings",
            "backend_kind": "local",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "source_id": "sentence-transformers/all-MiniLM-L6-v2",
        },
    )
    seen_config: dict[str, object] = {}

    def _update_provider_instance(_db, **kwargs):
        seen_config.update(kwargs["config_json"])
        return {
            "id": kwargs["provider_instance_id"],
            "slug": kwargs["slug"],
            "provider_key": "vllm_embeddings_local",
            "capability_key": "embeddings",
            "adapter_kind": "openai_compatible_embeddings",
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": kwargs["config_json"],
        }

    monkeypatch.setattr(platform_service.platform_repo, "update_provider_instance", _update_provider_instance)
    monkeypatch.setattr(platform_service, "_provider_runtime_inventory", lambda _row: ([], 200))

    payload = platform_service.assign_provider_loaded_model(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        provider_instance_id="provider-1",
        managed_model_id="sentence-transformers--all-MiniLM-L6-v2",
    )

    assert seen_config["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert seen_config["loaded_runtime_model_id"] == "/models/llm/sentence-transformers--all-MiniLM-L6-v2"
    assert payload["load_state"] == "loading"


def test_reconcile_provider_local_slot_reloads_persisted_model_when_runtime_is_empty(monkeypatch: pytest.MonkeyPatch):
    provider_row = {
        "id": "provider-embeddings",
        "slug": "vllm-embeddings-local",
        "provider_key": "vllm_embeddings_local",
        "capability_key": "embeddings",
        "adapter_kind": "openai_compatible_embeddings",
        "display_name": "vLLM embeddings local",
        "description": "desc",
        "endpoint_url": "http://llm:8000",
        "healthcheck_url": "http://llm:8000/health",
        "enabled": True,
        "config_json": {
            "runtime_admin_base_url": "http://llm_runtime_embeddings:8000",
            "loaded_managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "loaded_managed_model_name": "all-MiniLM-L6-v2",
            "loaded_runtime_model_id": "None",
            "loaded_local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "loaded_source_id": "sentence-transformers/all-MiniLM-L6-v2",
            "load_state": "loading",
        },
    }
    load_calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        platform_service._platform_local_slots_module,
        "_runtime_admin_state",
        lambda _row: (
            {
                "capability": "embeddings",
                "load_state": "empty",
                "runtime_model_id": None,
                "local_path": None,
                "managed_model_id": None,
                "display_name": None,
                "last_error": None,
            },
            200,
        ),
    )
    monkeypatch.setattr(
        platform_service._platform_local_slots_module,
        "_runtime_admin_load_model",
        lambda _row, *, runtime_model_id, local_path, managed_model_id, display_name: (
            load_calls.append(
                {
                    "runtime_model_id": runtime_model_id,
                    "local_path": local_path,
                    "managed_model_id": managed_model_id,
                    "display_name": display_name,
                }
            )
            or {
                "capability": "embeddings",
                "load_state": "loading",
                "runtime_model_id": runtime_model_id,
                "local_path": local_path,
                "managed_model_id": managed_model_id,
                "display_name": display_name,
                "last_error": None,
            },
            200,
        ),
    )

    def _update_provider_instance(_db, **kwargs):
        return {
            "id": kwargs["provider_instance_id"],
            "slug": kwargs["slug"],
            "provider_key": "vllm_embeddings_local",
            "capability_key": "embeddings",
            "adapter_kind": "openai_compatible_embeddings",
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": dict(kwargs["config_json"]),
        }

    monkeypatch.setattr(platform_service.platform_repo, "update_provider_instance", _update_provider_instance)

    reconciled = platform_service._platform_local_slots_module.reconcile_provider_local_slot(
        "ignored",
        provider_row=provider_row,
    )

    assert load_calls == [
        {
            "runtime_model_id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "display_name": "all-MiniLM-L6-v2",
        }
    ]
    assert reconciled["config_json"]["load_state"] == "loading"
    assert reconciled["config_json"]["loaded_managed_model_id"] == "sentence-transformers--all-MiniLM-L6-v2"


def test_reconcile_provider_local_slot_hydrates_provider_rows_missing_capability_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    provider_row = {
        "id": "provider-embeddings",
        "slug": "vllm-embeddings-local",
        "provider_key": "vllm_embeddings_local",
        "display_name": "vLLM embeddings local",
        "description": "desc",
        "endpoint_url": "http://llm:8000",
        "healthcheck_url": "http://llm:8000/health",
        "enabled": True,
        "config_json": {
            "runtime_admin_base_url": "http://llm_runtime_embeddings:8000",
            "loaded_managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "loaded_managed_model_name": "all-MiniLM-L6-v2",
            "loaded_runtime_model_id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "loaded_local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "loaded_source_id": "sentence-transformers/all-MiniLM-L6-v2",
            "load_state": "loading",
        },
    }
    hydrated_provider_row = {
        **provider_row,
        "capability_key": "embeddings",
        "adapter_kind": "openai_compatible_embeddings",
    }
    load_calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: hydrated_provider_row if provider_instance_id == "provider-embeddings" else None,
    )
    monkeypatch.setattr(
        platform_service._platform_local_slots_module,
        "_runtime_admin_state",
        lambda _row: (
            {
                "capability": "embeddings",
                "load_state": "empty",
                "runtime_model_id": None,
                "local_path": None,
                "managed_model_id": None,
                "display_name": None,
                "last_error": None,
            },
            200,
        ),
    )
    monkeypatch.setattr(
        platform_service._platform_local_slots_module,
        "_runtime_admin_load_model",
        lambda _row, *, runtime_model_id, local_path, managed_model_id, display_name: (
            load_calls.append(
                {
                    "runtime_model_id": runtime_model_id,
                    "local_path": local_path,
                    "managed_model_id": managed_model_id,
                    "display_name": display_name,
                }
            )
            or {
                "capability": "embeddings",
                "load_state": "loading",
                "runtime_model_id": runtime_model_id,
                "local_path": local_path,
                "managed_model_id": managed_model_id,
                "display_name": display_name,
                "last_error": None,
            },
            200,
        ),
    )

    def _update_provider_instance(_db, **kwargs):
        return {
            "id": kwargs["provider_instance_id"],
            "slug": kwargs["slug"],
            "provider_key": "vllm_embeddings_local",
            "capability_key": "embeddings",
            "adapter_kind": "openai_compatible_embeddings",
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": dict(kwargs["config_json"]),
        }

    monkeypatch.setattr(platform_service.platform_repo, "update_provider_instance", _update_provider_instance)

    reconciled = platform_service._platform_local_slots_module.reconcile_provider_local_slot(
        "ignored",
        provider_row=provider_row,
    )

    assert load_calls == [
        {
            "runtime_model_id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "display_name": "all-MiniLM-L6-v2",
        }
    ]
    assert reconciled["config_json"]["load_state"] == "loading"


def test_clear_provider_loaded_model_resets_local_slot(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: {
            "id": provider_instance_id,
            "slug": "vllm-local-gateway",
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
            "adapter_kind": "openai_compatible_llm",
            "display_name": "vLLM local gateway",
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {
                "loaded_managed_model_id": "Qwen--Qwen2.5-0.5B-Instruct",
                "loaded_managed_model_name": "Qwen",
                "loaded_runtime_model_id": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
                "load_state": "loaded",
            },
        },
    )

    def _update_provider_instance(_db, **kwargs):
        return {
            "id": kwargs["provider_instance_id"],
            "slug": kwargs["slug"],
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
            "adapter_kind": "openai_compatible_llm",
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": kwargs["config_json"],
        }

    monkeypatch.setattr(platform_service.platform_repo, "update_provider_instance", _update_provider_instance)
    monkeypatch.setattr(platform_service, "_provider_runtime_inventory", lambda _row: ([], 200))

    payload = platform_service.clear_provider_loaded_model(
        "ignored",
        config=object(),  # type: ignore[arg-type]
        provider_instance_id="provider-1",
    )

    assert payload["loaded_managed_model_id"] is None
    assert payload["loaded_runtime_model_id"] is None
    assert payload["load_state"] == "empty"


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


def test_openai_adapter_uses_configured_request_timeout_for_chat_requests(monkeypatch: pytest.MonkeyPatch):
    seen_timeouts: list[float] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del url, method, payload, headers
        seen_timeouts.append(timeout_seconds)
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
            config={"request_timeout_seconds": 15},
            binding_config={},
            deployment_profile_id="deployment-1",
            deployment_profile_slug="local-default",
            deployment_profile_display_name="Local Default",
        )
    )

    payload, status_code = adapter.chat_completion(
        model="local-vllm-default",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        max_tokens=None,
        temperature=None,
        allow_local_fallback=True,
    )

    assert status_code == 200
    assert payload is not None
    assert seen_timeouts == [15.0]


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


def test_openai_embeddings_adapter_lists_normalized_embeddings_resources(monkeypatch: pytest.MonkeyPatch):
    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del url, method, payload, headers, timeout_seconds
        return {
            "object": "list",
            "data": [
                {
                    "id": "text-only-model",
                    "name": "Text Only",
                    "owned_by": "local_vllm",
                    "capabilities": {"text": True, "image_input": False, "embeddings": False},
                },
                {
                    "id": "local-vllm-embeddings-default",
                    "name": "Local Embeddings",
                    "owned_by": "local_vllm",
                    "source_id": "hf/local-embeddings",
                    "capabilities": {"text": False, "image_input": False, "embeddings": True},
                },
            ],
        }, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.OpenAICompatibleEmbeddingsAdapter(
        platform_service.ProviderBinding(
            capability_key="embeddings",
            provider_instance_id="provider-1",
            provider_slug="vllm-embeddings-local",
            provider_key="vllm_embeddings_local",
            provider_display_name="vLLM embeddings local",
            provider_description="desc",
            endpoint_url="http://llm:8000",
            healthcheck_url="http://llm:8000/health",
            enabled=True,
            adapter_kind="openai_compatible_embeddings",
            config={"models_path": "/v1/models"},
            binding_config={},
            deployment_profile_id="deployment-1",
            deployment_profile_slug="local-default",
            deployment_profile_display_name="Local Default",
        )
    )

    resources, status_code = adapter.list_resources()

    assert status_code == 200
    assert resources == [
        {
            "id": "local-vllm-embeddings-default",
            "resource_kind": "model",
            "ref_type": "provider_resource",
            "managed_model_id": None,
            "provider_resource_id": "local-vllm-embeddings-default",
            "display_name": "local-vllm-embeddings-default",
            "metadata": {
                "name": "Local Embeddings",
                "provider_model_id": "local-vllm-embeddings-default",
                "source_id": "hf/local-embeddings",
                "owned_by": "local_vllm",
            },
        }
    ]


def test_validate_provider_supports_embeddings_capability(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "get_active_binding_for_provider_instance",
        lambda _db, *, provider_instance_id: {
            "capability_key": "embeddings",
            "provider_instance_id": provider_instance_id,
            "provider_slug": "vllm-embeddings-local",
            "provider_key": "vllm_embeddings_local",
            "provider_display_name": "vLLM embeddings local",
            "provider_description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {"embeddings_path": "/v1/embeddings"},
            "binding_config": {},
            "adapter_kind": "openai_compatible_embeddings",
            "deployment_profile_id": "deployment-1",
            "deployment_profile_slug": "local-default",
            "deployment_profile_display_name": "Local Default",
            "resources": [
                {
                    "id": "local-embed",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "local-embed",
                    "provider_resource_id": "local-vllm-embeddings-default",
                    "display_name": "Local Embed",
                    "metadata": {
                        "provider": "huggingface",
                        "backend": "local",
                        "task_key": "embeddings",
                        "provider_model_id": "local-vllm-embeddings-default",
                        "local_path": "/models/embed",
                        "source_id": "hf/local-embed",
                        "availability": "offline_ready",
                    },
                }
            ],
            "default_resource_id": "local-embed",
            "default_resource": {
                "id": "local-embed",
                "resource_kind": "model",
                "ref_type": "managed_model",
                "managed_model_id": "local-embed",
                "provider_resource_id": "local-vllm-embeddings-default",
                "display_name": "Local Embed",
                "metadata": {
                    "provider": "huggingface",
                    "backend": "local",
                    "task_key": "embeddings",
                    "provider_model_id": "local-vllm-embeddings-default",
                    "local_path": "/models/embed",
                    "source_id": "hf/local-embed",
                    "availability": "offline_ready",
                },
            },
        },
    )
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
                "config_json": {"embeddings_path": "/v1/embeddings"},
            },
    )
    monkeypatch.setattr(
        platform_service,
        "_adapter_from_binding",
        lambda binding: type(
            "FakeEmbeddingsAdapter",
            (),
            {
                "binding": binding,
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
        "resources_reachable": True,
        "resources_status_code": 200,
        "resources": [],
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
            "model": "allowed-model",
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
    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: [])
    monkeypatch.setattr(platform_service.platform_repo, "list_deployment_bindings", lambda _db, *, deployment_profile_id: [])
    monkeypatch.setattr(platform_service.platform_repo, "get_provider_instance", lambda _db, provider_instance_id: None)

    def _ensure_provider_instance(_db, **kwargs):
        return {"id": f"{kwargs['slug']}-id"}

    def _ensure_deployment_profile(_db, *, slug, **kwargs):
        created_profiles.append(slug)
        return {"id": f"{slug}-id"}

    def _upsert_deployment_binding(
        _db,
        *,
        deployment_profile_id,
        capability_key,
        provider_instance_id,
        resources,
        default_resource_id,
        binding_config,
        resource_policy,
    ):
        del resources
        del default_resource_id
        del binding_config
        del resource_policy
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


def test_ensure_platform_bootstrap_state_reconciles_local_provider_slots(monkeypatch: pytest.MonkeyPatch):
    reconciled_provider_ids: list[str] = []

    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: [])
    monkeypatch.setattr(platform_service.platform_repo, "list_deployment_bindings", lambda _db, *, deployment_profile_id: [])
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", lambda _db, **kwargs: {"id": f"{kwargs['slug']}-id", "slug": kwargs["slug"]})
    monkeypatch.setattr(
        platform_bootstrap,
        "reconcile_local_provider_slots",
        lambda _db, *, provider_rows: reconciled_provider_ids.extend(str(item.get("id")) for item in provider_rows) or provider_rows,
    )
    monkeypatch.setattr(platform_service.platform_repo, "ensure_deployment_profile", lambda _db, *, slug, **kwargs: {"id": f"{slug}-id"})
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

    assert reconciled_provider_ids == [
        "vllm-local-gateway-id",
        "vllm-embeddings-local-id",
        "llama-cpp-local-id",
    ]


def test_ensure_platform_bootstrap_state_skips_llama_cpp_profile_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    created_profiles: list[str] = []

    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: [])
    monkeypatch.setattr(platform_service.platform_repo, "list_deployment_bindings", lambda _db, *, deployment_profile_id: [])
    monkeypatch.setattr(platform_service.platform_repo, "get_provider_instance", lambda _db, provider_instance_id: None)
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
    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: [])
    monkeypatch.setattr(platform_service.platform_repo, "list_deployment_bindings", lambda _db, *, deployment_profile_id: [])
    monkeypatch.setattr(platform_service.platform_repo, "get_provider_instance", lambda _db, provider_instance_id: None)
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", lambda _db, **kwargs: {"id": f"{kwargs['slug']}-id"})
    monkeypatch.setattr(
        platform_service.platform_repo,
        "ensure_deployment_profile",
        lambda _db, *, slug, **kwargs: created_profiles.append(slug) or {"id": f"{slug}-id"},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "upsert_deployment_binding",
        lambda _db, *, deployment_profile_id, capability_key, provider_instance_id, resources, default_resource_id, binding_config, resource_policy: (
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


@pytest.mark.parametrize(
    ("slug", "provider_key", "capability_key", "runtime_model_id"),
    [
        (
            "vllm-embeddings-local",
            "vllm_embeddings_local",
            "embeddings",
            "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        ),
        (
            "vllm-local-gateway",
            "vllm_local",
            "llm_inference",
            "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
        ),
    ],
)
def test_list_providers_preserves_loaded_model_slot_during_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    provider_key: str,
    capability_key: str,
    runtime_model_id: str,
):
    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "list_deployment_bindings", lambda _db, *, deployment_profile_id: [])
    monkeypatch.setattr(platform_bootstrap, "reconcile_local_provider_slots", lambda _db, *, provider_rows: provider_rows)
    monkeypatch.setattr(
        platform_service,
        "_effective_local_slot",
        lambda row: platform_service._local_slot_payload_from_config(dict(row.get("config_json") or {})),  # type: ignore[attr-defined]
    )

    providers_by_slug: dict[str, dict[str, object]] = {
        slug: {
            "id": f"{slug}-id",
            "slug": slug,
            "provider_key": provider_key,
            "capability_key": capability_key,
            "adapter_kind": "openai_compatible_embeddings" if capability_key == "embeddings" else "openai_compatible_llm",
            "display_name": slug,
            "description": "desc",
            "endpoint_url": "http://llm:8000",
            "healthcheck_url": "http://llm:8000/health",
            "enabled": True,
            "config_json": {
                "loaded_managed_model_id": "model-1",
                "loaded_managed_model_name": "Model One",
                "loaded_runtime_model_id": runtime_model_id,
                "loaded_local_path": runtime_model_id,
                "load_state": "loaded",
            },
        }
    }

    def _ensure_provider_instance(_db, **kwargs):
        row = {
            "id": providers_by_slug.get(kwargs["slug"], {}).get("id", f"{kwargs['slug']}-id"),
            "slug": kwargs["slug"],
            "provider_key": kwargs["provider_key"],
            "capability_key": (
                "vector_store"
                if kwargs["provider_key"] in {"weaviate_local", "qdrant_local"}
                else ("embeddings" if kwargs["provider_key"] == "vllm_embeddings_local" else "llm_inference")
            ),
            "adapter_kind": (
                "weaviate_http"
                if kwargs["provider_key"] == "weaviate_local"
                else ("openai_compatible_embeddings" if kwargs["provider_key"] == "vllm_embeddings_local" else "openai_compatible_llm")
            ),
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": dict(kwargs["config_json"]),
        }
        providers_by_slug[kwargs["slug"]] = row
        return dict(row)

    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: list(providers_by_slug.values()))
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", _ensure_provider_instance)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "ensure_deployment_profile",
        lambda _db, *, slug, **kwargs: {"id": f"{slug}-id", "slug": slug, "display_name": slug, "description": "", "is_active": slug == "local-default"},
    )
    monkeypatch.setattr(platform_service.platform_repo, "upsert_deployment_binding", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "get_active_deployment", lambda _db: {"deployment_profile_id": "local-default-id"})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *args, **kwargs: {})

    config = SimpleNamespace(
        llm_url="http://llm:8000",
        llm_runtime_url="http://llm_runtime:8000",
        weaviate_url="http://weaviate:8080",
        llama_cpp_url="",
        qdrant_url="",
    )

    providers = platform_service.list_providers("ignored", config)  # type: ignore[arg-type]
    provider = next(item for item in providers if item["slug"] == slug)

    assert provider["loaded_managed_model_id"] == "model-1"
    assert provider["loaded_managed_model_name"] == "Model One"
    assert provider["loaded_runtime_model_id"] == runtime_model_id
    assert provider["load_state"] == "loaded"


@pytest.mark.parametrize(
    ("capability_key", "provider_slug", "provider_key", "adapter_kind"),
    [
        ("embeddings", "vllm-embeddings-local", "vllm_embeddings_local", "openai_compatible_embeddings"),
        ("llm_inference", "vllm-local-gateway", "vllm_local", "openai_compatible_llm"),
    ],
)
def test_list_deployment_profiles_preserves_model_resources_during_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    capability_key: str,
    provider_slug: str,
    provider_key: str,
    adapter_kind: str,
):
    monkeypatch.setattr(platform_service.platform_repo, "ensure_capability", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_family", lambda *args, **kwargs: {})
    monkeypatch.setattr(platform_bootstrap, "reconcile_local_provider_slots", lambda _db, *, provider_rows: provider_rows)

    providers_by_slug: dict[str, dict[str, object]] = {}

    def _ensure_provider_instance(_db, **kwargs):
        row = {
            "id": providers_by_slug.get(kwargs["slug"], {}).get("id", f"{kwargs['slug']}-id"),
            "slug": kwargs["slug"],
            "provider_key": kwargs["provider_key"],
            "capability_key": (
                "vector_store"
                if kwargs["provider_key"] in {"weaviate_local", "qdrant_local"}
                else ("embeddings" if kwargs["provider_key"] == "vllm_embeddings_local" else "llm_inference")
            ),
            "adapter_kind": (
                "weaviate_http"
                if kwargs["provider_key"] == "weaviate_local"
                else ("openai_compatible_embeddings" if kwargs["provider_key"] == "vllm_embeddings_local" else "openai_compatible_llm")
            ),
            "display_name": kwargs["display_name"],
            "description": kwargs["description"],
            "endpoint_url": kwargs["endpoint_url"],
            "healthcheck_url": kwargs["healthcheck_url"],
            "enabled": kwargs["enabled"],
            "config_json": dict(kwargs["config_json"]),
        }
        providers_by_slug[kwargs["slug"]] = row
        return dict(row)

    resource = {
        "id": "model-1",
        "resource_kind": "model",
        "ref_type": "managed_model",
        "managed_model_id": "model-1",
        "provider_resource_id": "provider-model-1",
        "display_name": "Model One",
        "metadata": {"name": "Model One", "task_key": capability_key},
        "is_default": True,
        "sort_order": 0,
    }
    bindings_by_profile: dict[str, list[dict[str, object]]] = {
        "local-default-id": [
            {
                "id": f"{capability_key}-binding-id",
                "capability_key": capability_key,
                "provider_instance_id": f"{provider_slug}-id",
                "provider_slug": provider_slug,
                "provider_key": provider_key,
                "provider_display_name": provider_slug,
                "provider_description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "adapter_kind": adapter_kind,
                "binding_config": {},
                "resource_policy": {},
                "resources": [dict(resource)],
                "default_resource_id": "model-1",
                "default_resource": dict(resource),
            }
        ]
    }

    def _upsert_deployment_binding(
        _db,
        *,
        deployment_profile_id,
        capability_key,
        provider_instance_id,
        resources,
        default_resource_id,
        binding_config,
        resource_policy,
    ):
        provider = next(
            row for row in providers_by_slug.values() if row["id"] == provider_instance_id
        )
        binding_row = {
            "id": f"{capability_key}-binding-id",
            "capability_key": capability_key,
            "provider_instance_id": provider_instance_id,
            "provider_slug": provider["slug"],
            "provider_key": provider["provider_key"],
            "provider_display_name": provider["display_name"],
            "provider_description": provider["description"],
            "endpoint_url": provider["endpoint_url"],
            "healthcheck_url": provider["healthcheck_url"],
            "enabled": provider["enabled"],
            "adapter_kind": provider["adapter_kind"],
            "binding_config": dict(binding_config),
            "resource_policy": dict(resource_policy),
            "resources": [dict(item) for item in resources],
            "default_resource_id": default_resource_id,
            "default_resource": next(
                (dict(item) for item in resources if str(item.get("id") or "").strip() == str(default_resource_id or "").strip()),
                None,
            ),
        }
        existing = bindings_by_profile.setdefault(deployment_profile_id, [])
        for index, item in enumerate(existing):
            if item["capability_key"] == capability_key:
                existing[index] = binding_row
                break
        else:
            existing.append(binding_row)
        return dict(binding_row)

    monkeypatch.setattr(platform_service.platform_repo, "list_provider_instances", lambda _db: list(providers_by_slug.values()))
    monkeypatch.setattr(platform_service.platform_repo, "ensure_provider_instance", _ensure_provider_instance)
    monkeypatch.setattr(
        platform_service.platform_repo,
        "ensure_deployment_profile",
        lambda _db, *, slug, **kwargs: {"id": f"{slug}-id", "slug": slug, "display_name": slug, "description": "", "is_active": slug == "local-default"},
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_profiles",
        lambda _db: [{"id": "local-default-id", "slug": "local-default", "display_name": "Local Default", "description": "", "is_active": True}],
    )
    monkeypatch.setattr(
        platform_service.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [dict(item) for item in bindings_by_profile.get(deployment_profile_id, [])],
    )
    monkeypatch.setattr(platform_service.platform_repo, "upsert_deployment_binding", _upsert_deployment_binding)
    monkeypatch.setattr(platform_service.platform_repo, "get_active_deployment", lambda _db: {"deployment_profile_id": "local-default-id"})
    monkeypatch.setattr(platform_service.platform_repo, "activate_deployment_profile", lambda *args, **kwargs: {})

    config = SimpleNamespace(
        llm_url="http://llm:8000",
        llm_runtime_url="http://llm_runtime:8000",
        weaviate_url="http://weaviate:8080",
        llama_cpp_url="",
        qdrant_url="",
    )

    deployments = platform_service.list_deployment_profiles("ignored", config)  # type: ignore[arg-type]
    deployment = next(item for item in deployments if item["slug"] == "local-default")
    binding = next(item for item in deployment["bindings"] if item["capability"] == capability_key)

    assert binding["default_resource_id"] == "model-1"
    assert binding["resources"][0]["managed_model_id"] == "model-1"


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
                "config_json": {"embeddings_path": "/v1/embeddings"},
                "binding_config": {},
                "adapter_kind": "openai_compatible_embeddings",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": deployment_slug,
                "deployment_profile_display_name": "Runtime Deployment",
                "resources": [
                    {
                        "id": "local-embed",
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": "local-embed",
                        "provider_resource_id": "local-vllm-embeddings-default",
                        "display_name": "Local Embed",
                        "metadata": {
                            "name": "Local Embed",
                            "provider": "huggingface",
                            "backend": "local",
                            "task_key": "embeddings",
                            "provider_model_id": "local-vllm-embeddings-default",
                            "local_path": "/models/embed",
                            "source_id": "hf/local-embed",
                            "availability": "offline_ready",
                        },
                    }
                ],
                "default_resource_id": "local-embed",
                "default_resource": {
                    "id": "local-embed",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "local-embed",
                    "provider_resource_id": "local-vllm-embeddings-default",
                    "display_name": "Local Embed",
                    "metadata": {
                        "name": "Local Embed",
                        "provider": "huggingface",
                        "backend": "local",
                        "task_key": "embeddings",
                        "provider_model_id": "local-vllm-embeddings-default",
                        "local_path": "/models/embed",
                        "source_id": "hf/local-embed",
                        "availability": "offline_ready",
                    },
                },
            }
        if capability_key == "sandbox_execution":
            return None
        if capability_key == "mcp_runtime":
            return None
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
                "resources": [],
                "default_resource_id": None,
                "default_resource": None,
                "resource_policy": {},
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
                "config": {"embeddings_path": "/v1/embeddings"},
                    "resources": [
                        {
                            "id": "local-embed",
                            "resource_kind": "model",
                            "ref_type": "managed_model",
                            "managed_model_id": "local-embed",
                            "knowledge_base_id": None,
                            "provider_resource_id": "local-vllm-embeddings-default",
                            "display_name": "Local Embed",
                            "metadata": {
                                "name": "Local Embed",
                                "provider": "huggingface",
                                "backend": "local",
                                "task_key": "embeddings",
                                "provider_model_id": "local-vllm-embeddings-default",
                                "local_path": "/models/embed",
                                "source_id": "hf/local-embed",
                                "availability": "offline_ready",
                            },
                            "name": "Local Embed",
                            "provider": "huggingface",
                            "backend": "local",
                            "task_key": "embeddings",
                            "provider_model_id": "local-vllm-embeddings-default",
                        "local_path": "/models/embed",
                        "source_id": "hf/local-embed",
                        "availability": "offline_ready",
                    }
                ],
                "default_resource_id": "local-embed",
                    "default_resource": {
                        "id": "local-embed",
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": "local-embed",
                        "knowledge_base_id": None,
                        "provider_resource_id": "local-vllm-embeddings-default",
                        "display_name": "Local Embed",
                        "metadata": {
                            "name": "Local Embed",
                            "provider": "huggingface",
                            "backend": "local",
                            "task_key": "embeddings",
                            "provider_model_id": "local-vllm-embeddings-default",
                            "local_path": "/models/embed",
                            "source_id": "hf/local-embed",
                            "availability": "offline_ready",
                        },
                        "name": "Local Embed",
                        "provider": "huggingface",
                        "backend": "local",
                    "task_key": "embeddings",
                    "provider_model_id": "local-vllm-embeddings-default",
                    "local_path": "/models/embed",
                    "source_id": "hf/local-embed",
                    "availability": "offline_ready",
                },
                "resource_policy": {},
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
                "resources": [],
                "default_resource_id": None,
                "default_resource": None,
                "resource_policy": {},
                "binding_config": {},
            },
        },
    }


def test_get_active_platform_runtime_includes_optional_tool_runtime_bindings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform_service, "ensure_platform_bootstrap_state", lambda _db, _config: None)

    def _active_binding(_db, *, capability_key):
        rows = {
            "llm_inference": {
                "capability_key": "llm_inference",
                "provider_instance_id": "provider-1",
                "provider_slug": "llm-provider",
                "provider_key": "vllm_local",
                "provider_display_name": "LLM Provider",
                "provider_description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {},
                "binding_config": {},
                "adapter_kind": "openai_compatible_llm",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": "local-default",
                "deployment_profile_display_name": "Local Default",
            },
            "embeddings": {
                "capability_key": "embeddings",
                "provider_instance_id": "provider-2",
                "provider_slug": "embeddings-provider",
                "provider_key": "vllm_embeddings_local",
                "provider_display_name": "Embeddings Provider",
                "provider_description": "desc",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config_json": {},
                "binding_config": {},
                "adapter_kind": "openai_compatible_embeddings",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": "local-default",
                "deployment_profile_display_name": "Local Default",
                "resources": [
                    {
                        "id": "local-embed",
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": "local-embed",
                        "provider_resource_id": "local-vllm-embeddings-default",
                        "display_name": "Local Embed",
                        "metadata": {
                            "name": "Local Embed",
                            "provider": "huggingface",
                            "backend": "local",
                            "task_key": "embeddings",
                            "provider_model_id": "local-vllm-embeddings-default",
                            "local_path": "/models/embed",
                            "source_id": "hf/local-embed",
                            "availability": "offline_ready",
                        },
                    }
                ],
                "default_resource_id": "local-embed",
                "default_resource": {
                    "id": "local-embed",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "local-embed",
                    "provider_resource_id": "local-vllm-embeddings-default",
                    "display_name": "Local Embed",
                    "metadata": {
                        "name": "Local Embed",
                        "provider": "huggingface",
                        "backend": "local",
                        "task_key": "embeddings",
                        "provider_model_id": "local-vllm-embeddings-default",
                        "local_path": "/models/embed",
                        "source_id": "hf/local-embed",
                        "availability": "offline_ready",
                    },
                },
            },
            "vector_store": {
                "capability_key": "vector_store",
                "provider_instance_id": "provider-3",
                "provider_slug": "weaviate-local",
                "provider_key": "weaviate_local",
                "provider_display_name": "Weaviate local",
                "provider_description": "desc",
                "endpoint_url": "http://weaviate:8080",
                "healthcheck_url": "http://weaviate:8080/v1/.well-known/ready",
                "enabled": True,
                "config_json": {},
                "binding_config": {},
                "adapter_kind": "weaviate_http",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": "local-default",
                "deployment_profile_display_name": "Local Default",
            },
            "sandbox_execution": {
                "capability_key": "sandbox_execution",
                "provider_instance_id": "provider-4",
                "provider_slug": "sandbox-local",
                "provider_key": "sandbox_local",
                "provider_display_name": "Sandbox local",
                "provider_description": "desc",
                "endpoint_url": "http://sandbox:6000",
                "healthcheck_url": "http://sandbox:6000/health",
                "enabled": True,
                "config_json": {"execute_path": "/v1/execute"},
                "binding_config": {},
                "adapter_kind": "sandbox_http",
                "deployment_profile_id": "deployment-1",
                "deployment_profile_slug": "local-default",
                "deployment_profile_display_name": "Local Default",
            },
        }
        return rows.get(capability_key)

    monkeypatch.setattr(platform_service.platform_repo, "get_active_binding_for_capability", _active_binding)

    payload = platform_service.get_active_platform_runtime("ignored", object())  # type: ignore[arg-type]

    assert payload["capabilities"]["sandbox_execution"]["provider_key"] == "sandbox_local"
