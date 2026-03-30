from __future__ import annotations

from types import SimpleNamespace

from app.services import context_management_vectorization
from app.services import platform_service
from app.services.platform_types import PlatformControlPlaneError


def test_list_vectorization_options_keeps_embeddings_provider_when_no_resources(monkeypatch):
    monkeypatch.setattr(
        context_management_vectorization.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: {
            "id": provider_instance_id,
            "provider_key": "weaviate_local",
            "capability_key": "vector_store",
            "display_name": "Weaviate local",
            "enabled": True,
        },
    )
    monkeypatch.setattr(
        context_management_vectorization.platform_repo,
        "list_provider_instances",
        lambda _db: [
            {
                "id": "embedding-provider-1",
                "slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "capability_key": "embeddings",
                "display_name": "vLLM embeddings local",
                "enabled": True,
            }
        ],
    )
    monkeypatch.setattr(
        context_management_vectorization.platform_repo,
        "get_active_binding_for_provider_instance",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        context_management_vectorization,
        "_serialize_provider_summary",
        lambda row: {
            "id": str(row.get("id") or ""),
            "slug": str(row.get("slug") or "") or None,
            "provider_key": str(row.get("provider_key") or "") or None,
            "display_name": str(row.get("display_name") or "") or None,
            "enabled": row.get("enabled"),
            "capability": str(row.get("capability_key") or "") or None,
        },
    )

    class _Adapter:
        def list_resources(self):
            return [], 200

    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: _Adapter(),
    )

    payload = context_management_vectorization.list_vectorization_options(
        "postgresql://ignored",
        config=SimpleNamespace(),
        backing_provider_instance_id="vector-provider-1",
    )

    assert payload["embedding_providers"] == [
        {
            "id": "embedding-provider-1",
            "slug": "vllm-embeddings-local",
            "provider_key": "vllm_embeddings_local",
            "display_name": "vLLM embeddings local",
            "enabled": True,
            "capability": "embeddings",
            "resources": [],
            "default_resource_id": None,
            "is_ready": False,
            "unavailable_reason": "no_embedding_resources",
        }
    ]


def test_list_vectorization_options_skips_embeddings_provider_when_resolution_fails(monkeypatch):
    monkeypatch.setattr(
        context_management_vectorization.platform_repo,
        "get_provider_instance",
        lambda _db, provider_instance_id: {
            "id": provider_instance_id,
            "provider_key": "weaviate_local",
            "capability_key": "vector_store",
            "display_name": "Weaviate local",
            "enabled": True,
        },
    )
    monkeypatch.setattr(
        context_management_vectorization.platform_repo,
        "list_provider_instances",
        lambda _db: [
            {
                "id": "embedding-provider-1",
                "slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "capability_key": "embeddings",
                "display_name": "vLLM embeddings local",
                "enabled": True,
            }
        ],
    )

    def _raise_resolution_error(*_args, **_kwargs):
        raise PlatformControlPlaneError("provider_unavailable", "provider unavailable", status_code=503)

    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        _raise_resolution_error,
    )

    payload = context_management_vectorization.list_vectorization_options(
        "postgresql://ignored",
        config=SimpleNamespace(),
        backing_provider_instance_id="vector-provider-1",
    )

    assert payload["embedding_providers"] == []
