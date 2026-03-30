from __future__ import annotations

import pytest

from app.services import context_management_serialization
from app.services.platform_types import PlatformControlPlaneError


def test_normalize_knowledge_base_payload_requires_backing_provider_instance_id_on_create():
    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            {
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
            },
            is_create=True,
        )

    assert exc_info.value.code == "invalid_backing_provider_instance_id"


def test_normalize_knowledge_base_payload_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(context_management_serialization.platform_repo, "get_provider_instance", lambda *_args, **_kwargs: None)

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            {
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
                "backing_provider_instance_id": "provider-missing",
            },
            is_create=True,
        )

    assert exc_info.value.code == "backing_provider_not_found"


def test_normalize_knowledge_base_payload_rejects_non_vector_store_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_serialization.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "provider-1",
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
            "enabled": True,
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            {
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
                "backing_provider_instance_id": "provider-1",
            },
            is_create=True,
        )

    assert exc_info.value.code == "invalid_backing_provider_capability"


def test_normalize_knowledge_base_payload_rejects_disabled_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_serialization.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "provider-2",
            "provider_key": "weaviate_local",
            "capability_key": "vector_store",
            "enabled": False,
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            {
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
                "backing_provider_instance_id": "provider-2",
            },
            is_create=True,
        )

    assert exc_info.value.code == "invalid_backing_provider_disabled"


def test_normalize_schema_profile_payload_requires_vector_store_provider_family(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_serialization.platform_repo,
        "get_provider_family",
        lambda *_args, **_kwargs: {
            "provider_key": "vllm_local",
            "capability_key": "llm_inference",
        },
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_schema_profile_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            {
                "slug": "llm-only",
                "display_name": "LLM only",
                "provider_key": "vllm_local",
                "schema": {"properties": [{"name": "subject", "data_type": "text"}]},
            },
        )

    assert exc_info.value.code == "invalid_schema_profile_provider_capability"


def test_serialize_schema_profile_returns_expected_shape():
    payload = context_management_serialization._serialize_schema_profile(  # type: ignore[attr-defined]
        {
            "id": "profile-1",
            "slug": "plain-document-rag",
            "display_name": "Plain document RAG",
            "description": "General-purpose retrieval schema.",
            "provider_key": "weaviate_local",
            "is_system": True,
            "schema_json": {"properties": [{"name": "title", "data_type": "text"}]},
        }
    )

    assert payload == {
        "id": "profile-1",
        "slug": "plain-document-rag",
        "display_name": "Plain document RAG",
        "description": "General-purpose retrieval schema.",
        "provider_key": "weaviate_local",
        "is_system": True,
        "schema": {"properties": [{"name": "title", "data_type": "text"}]},
        "created_at": None,
        "updated_at": None,
    }


def test_serialize_knowledge_base_includes_vectorization_summary():
    payload = context_management_serialization._serialize_knowledge_base(  # type: ignore[attr-defined]
        {
            "id": "kb-primary",
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "backing_provider_slug": "weaviate-local",
            "backing_provider_display_name": "Weaviate local",
            "backing_provider_enabled": True,
            "backing_provider_capability": "vector_store",
            "vectorization_mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "text-embedding-3-small",
            "embedding_provider_slug": "embeddings-local",
            "embedding_provider_key": "openai_compatible_cloud_embeddings",
            "embedding_provider_display_name": "Embeddings local",
            "embedding_provider_enabled": True,
            "embedding_provider_capability": "embeddings",
            "vectorization_json": {
                "supports_named_vectors": True,
                "embedding_resource": {
                    "id": "text-embedding-3-small",
                    "provider_resource_id": "text-embedding-3-small",
                    "display_name": "text-embedding-3-small",
                    "metadata": {"dimension": 1536},
                },
            },
            "lifecycle_state": "active",
            "sync_status": "ready",
            "schema_json": {},
            "document_count": 0,
            "binding_count": 0,
        }
    )

    assert payload["vectorization"] == {
        "mode": "vanessa_embeddings",
        "embedding_provider_instance_id": "embedding-provider-1",
        "embedding_resource_id": "text-embedding-3-small",
        "embedding_provider": {
            "id": "embedding-provider-1",
            "slug": "embeddings-local",
            "provider_key": "openai_compatible_cloud_embeddings",
            "display_name": "Embeddings local",
            "enabled": True,
            "capability": "embeddings",
        },
        "embedding_resource": {
            "id": "text-embedding-3-small",
            "provider_resource_id": "text-embedding-3-small",
            "display_name": "text-embedding-3-small",
            "metadata": {"dimension": 1536},
        },
        "supports_named_vectors": True,
    }
