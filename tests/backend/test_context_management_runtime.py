from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import context_management_runtime, context_management_vectorization, platform_service
from app.services.platform_types import PlatformControlPlaneError


def test_query_knowledge_base_rejects_active_provider_instance_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        context_management_vectorization,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.1, 0.2]]},
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-9", provider_key="qdrant_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_provider_mismatch"
    assert exc_info.value.details == {
        "knowledge_base_id": "kb-primary",
        "knowledge_base_provider_instance_id": "provider-2",
        "active_provider_instance_id": "provider-9",
        "knowledge_base_provider_key": "weaviate_local",
        "active_provider_key": "qdrant_local",
    }


def test_query_knowledge_base_rejects_self_provided_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "self_provided",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-small"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_self_provided_query_unsupported"


def test_query_knowledge_base_rejects_embeddings_target_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_runtime,
        "_require_knowledge_base",
        lambda _db, _knowledge_base_id: {
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_resource_id": "text-embedding-3-small",
            "lifecycle_state": "active",
            "sync_status": "ready",
        },
    )
    monkeypatch.setattr(context_management_runtime, "_is_knowledge_base_eligible", lambda _row: True)
    monkeypatch.setattr(
        platform_service,
        "resolve_vector_store_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(provider_instance_id="provider-2", provider_key="weaviate_local"),
            query=lambda **_query_kwargs: {"index": "kb_product_docs", "results": []},
        ),
    )
    monkeypatch.setattr(
        platform_service,
        "resolve_embeddings_adapter",
        lambda *_args, **_kwargs: SimpleNamespace(
            binding=SimpleNamespace(
                provider_instance_id="embedding-provider-1",
                provider_key="openai_compatible_cloud_embeddings",
                default_resource={"provider_resource_id": "text-embedding-3-large"},
            ),
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_runtime.query_knowledge_base(
            "postgresql://ignored",
            config=object(),
            knowledge_base_id="kb-primary",
            payload={"query_text": "hello"},
        )

    assert exc_info.value.code == "knowledge_base_embeddings_resource_mismatch"
