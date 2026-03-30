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
