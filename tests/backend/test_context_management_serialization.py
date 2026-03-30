from __future__ import annotations

import pytest

from app.services import context_management_serialization
from app.services.platform_types import PlatformControlPlaneError


def test_normalize_knowledge_base_payload_requires_backing_provider_instance_id_on_create():
    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
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
