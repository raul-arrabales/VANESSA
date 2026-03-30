from __future__ import annotations

import pytest

from app.services import platform_deployment_status  # noqa: E402


def _binding(
    capability_key: str,
    *,
    provider_instance_id: str | None = None,
    enabled: bool = True,
    resources: list[dict[str, object]] | None = None,
    default_resource_id: str | None = None,
    resource_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": f"{capability_key}-binding",
        "capability_key": capability_key,
        "provider_instance_id": provider_instance_id or f"{capability_key}-provider",
        "provider_slug": f"{capability_key}-provider",
        "provider_key": f"{capability_key}_provider",
        "provider_display_name": capability_key,
        "provider_description": "desc",
        "endpoint_url": "http://example.invalid",
        "healthcheck_url": "http://example.invalid/health",
        "enabled": enabled,
        "adapter_kind": "adapter",
        "binding_config": {},
        "resource_policy": dict(resource_policy or {}),
        "resources": [dict(item) for item in resources or []],
        "default_resource_id": default_resource_id,
        "default_resource": next(
            (
                dict(item)
                for item in resources or []
                if str(item.get("id") or "").strip() == str(default_resource_id or "").strip()
            ),
            None,
        ),
    }


def _model_resource(
    model_id: str,
    *,
    provider_resource_id: str,
) -> dict[str, object]:
    return {
        "id": model_id,
        "resource_kind": "model",
        "ref_type": "managed_model",
        "managed_model_id": model_id,
        "provider_resource_id": provider_resource_id,
        "display_name": model_id,
        "metadata": {
            "provider_model_id": provider_resource_id,
            "task_key": "embeddings",
        },
    }


def _knowledge_base_resource(knowledge_base_id: str) -> dict[str, object]:
    return {
        "id": knowledge_base_id,
        "resource_kind": "knowledge_base",
        "ref_type": "knowledge_base",
        "knowledge_base_id": knowledge_base_id,
        "provider_resource_id": f"{knowledge_base_id}-index",
        "display_name": knowledge_base_id,
        "metadata": {},
    }


def test_compute_status_marks_model_binding_incomplete_without_resources():
    binding_statuses, deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding("llm_inference"),
            _binding("embeddings"),
            _binding("vector_store", resource_policy={"selection_mode": "explicit"}),
        ],
    )

    assert binding_statuses["embeddings"]["is_ready"] is False
    assert binding_statuses["embeddings"]["issues"][0]["code"] == "resources_missing"
    assert deployment_status["incomplete_capabilities"] == ["embeddings", "llm_inference", "vector_store"]


def test_compute_status_marks_model_binding_incomplete_without_default():
    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding(
                "embeddings",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
            )
        ],
    )

    assert binding_statuses["embeddings"]["is_ready"] is False
    assert binding_statuses["embeddings"]["issues"][0]["code"] == "default_resource_missing"


def test_compute_status_marks_vector_binding_incomplete_without_kbs():
    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding("vector_store", resource_policy={"selection_mode": "explicit"}),
        ],
    )

    assert binding_statuses["vector_store"]["is_ready"] is False
    assert binding_statuses["vector_store"]["issues"][0]["code"] == "resources_missing"


def test_compute_status_marks_dynamic_namespace_without_prefix():
    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding("vector_store", resource_policy={"selection_mode": "dynamic_namespace"}),
        ],
    )

    assert binding_statuses["vector_store"]["is_ready"] is False
    assert binding_statuses["vector_store"]["issues"][0]["code"] == "namespace_prefix_missing"


def test_compute_status_marks_self_provided_kb_unsupported(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_deployment_status.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "display_name": "KB Primary",
            "vectorization_mode": "self_provided",
            "embedding_provider_instance_id": None,
            "embedding_resource_id": None,
        },
    )

    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding(
                "embeddings",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
                default_resource_id="embed-model",
            ),
            _binding(
                "vector_store",
                resources=[_knowledge_base_resource("kb-primary")],
                default_resource_id="kb-primary",
                resource_policy={"selection_mode": "explicit"},
            ),
        ],
    )

    assert binding_statuses["vector_store"]["is_ready"] is False
    assert binding_statuses["vector_store"]["issues"][0]["code"] == "knowledge_base_self_provided_unsupported"


def test_compute_status_marks_kb_embeddings_provider_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_deployment_status.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "display_name": "KB Primary",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "different-provider",
            "embedding_resource_id": "text-embedding-3-small",
        },
    )

    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding(
                "embeddings",
                provider_instance_id="embeddings-provider",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
                default_resource_id="embed-model",
            ),
            _binding(
                "vector_store",
                resources=[_knowledge_base_resource("kb-primary")],
                default_resource_id="kb-primary",
                resource_policy={"selection_mode": "explicit"},
            ),
        ],
    )

    issue_codes = [issue["code"] for issue in binding_statuses["vector_store"]["issues"]]
    assert "knowledge_base_embeddings_provider_mismatch" in issue_codes


def test_compute_status_marks_kb_embeddings_resource_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_deployment_status.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "display_name": "KB Primary",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embeddings-provider",
            "embedding_resource_id": "text-embedding-3-large",
        },
    )

    binding_statuses, _deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding(
                "embeddings",
                provider_instance_id="embeddings-provider",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
                default_resource_id="embed-model",
            ),
            _binding(
                "vector_store",
                resources=[_knowledge_base_resource("kb-primary")],
                default_resource_id="kb-primary",
                resource_policy={"selection_mode": "explicit"},
            ),
        ],
    )

    issue_codes = [issue["code"] for issue in binding_statuses["vector_store"]["issues"]]
    assert "knowledge_base_embeddings_resource_mismatch" in issue_codes


def test_compute_status_returns_ready_for_fully_configured_deployment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        platform_deployment_status.context_repo,
        "get_knowledge_base",
        lambda _db, knowledge_base_id: {
            "id": knowledge_base_id,
            "display_name": "KB Primary",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embeddings-provider",
            "embedding_resource_id": "text-embedding-3-small",
        },
    )

    binding_statuses, deployment_status = platform_deployment_status.compute_deployment_configuration_status(
        "ignored",
        bindings=[
            _binding(
                "llm_inference",
                resources=[
                    {
                        "id": "llm-model",
                        "resource_kind": "model",
                        "ref_type": "managed_model",
                        "managed_model_id": "llm-model",
                        "provider_resource_id": "gpt-4.1-mini",
                        "display_name": "llm-model",
                        "metadata": {},
                    }
                ],
                default_resource_id="llm-model",
            ),
            _binding(
                "embeddings",
                provider_instance_id="embeddings-provider",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
                default_resource_id="embed-model",
            ),
            _binding(
                "vector_store",
                resources=[_knowledge_base_resource("kb-primary")],
                default_resource_id="kb-primary",
                resource_policy={"selection_mode": "explicit"},
            ),
        ],
    )

    assert binding_statuses["llm_inference"]["is_ready"] is True
    assert binding_statuses["embeddings"]["is_ready"] is True
    assert binding_statuses["vector_store"]["is_ready"] is True
    assert deployment_status == {
        "is_ready": True,
        "incomplete_capabilities": [],
        "summary": "All required capabilities are configured.",
    }


def test_serialize_deployment_profile_with_status_attaches_binding_and_deployment_status():
    deployment = platform_deployment_status.serialize_deployment_profile_with_status(
        "ignored",
        {
            "id": "deployment-1",
            "slug": "profile-a",
            "display_name": "Profile A",
            "description": "",
            "is_active": False,
        },
        [
            _binding(
                "embeddings",
                provider_instance_id="embeddings-provider",
                resources=[_model_resource("embed-model", provider_resource_id="text-embedding-3-small")],
                default_resource_id="embed-model",
            ),
        ],
    )

    assert deployment["bindings"][0]["configuration_status"] == {
        "is_ready": True,
        "issues": [],
        "summary": "Ready.",
    }
    assert deployment["configuration_status"] == {
        "is_ready": False,
        "incomplete_capabilities": ["llm_inference", "vector_store"],
        "summary": "2 required capabilities are not fully configured.",
    }
