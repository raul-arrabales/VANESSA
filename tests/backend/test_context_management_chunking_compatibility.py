from __future__ import annotations

import pytest

from app.services import context_management_chunking_compatibility
from app.services import context_management_serialization
from app.services import context_management_shared
from app.services.platform_types import PlatformControlPlaneError


def test_assert_knowledge_base_chunking_compatible_raises_standardized_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_management_chunking_compatibility,
        "resolve_knowledge_base_chunking_constraints",
        lambda *_args, **_kwargs: context_management_chunking_compatibility.EmbeddingsChunkingConstraints(
            max_input_tokens=256,
            special_tokens_per_input=2,
            safe_chunk_length_max=254,
        ),
    )

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_chunking_compatibility.assert_knowledge_base_chunking_compatible(
            "postgresql://ignored",
            knowledge_base={
                "id": "kb-primary",
                "embedding_resource_id": "local-embedding-model",
                "vectorization_json": {
                    "embedding_resource": {
                        "id": "local-embedding-model",
                        "provider_resource_id": "local-embedding-model",
                        "display_name": "sentence-transformers/all-MiniLM-L6-v2",
                    }
                },
                "chunking_strategy": "fixed_length",
                "chunking_config_json": {
                    "unit": "tokens",
                    "chunk_length": 300,
                    "chunk_overlap": 60,
                },
            },
            error_prefix="Unable to sync source 'Patient Guides'",
            status_code=409,
            details={"source_id": "source-1", "source_display_name": "Patient Guides"},
        )

    assert exc_info.value.code == "knowledge_base_chunking_exceeds_embeddings_limit"
    assert exc_info.value.status_code == 409
    assert (
        str(exc_info.value)
        == "Unable to sync source 'Patient Guides': chunk length 300 exceeds the safe maximum 254 tokens for "
        "embeddings model sentence-transformers/all-MiniLM-L6-v2 (model limit 256 including 2 special tokens). "
        "Update KB chunking to 254 or smaller and retry."
    )
    assert exc_info.value.details == {
        "knowledge_base_id": "kb-primary",
        "embedding_resource_id": "local-embedding-model",
        "embedding_model_display_name": "sentence-transformers/all-MiniLM-L6-v2",
        "chunk_length": 300,
        "chunk_overlap": 60,
        "max_input_tokens": 256,
        "special_tokens_per_input": 2,
        "safe_chunk_length_max": 254,
        "source_id": "source-1",
        "source_display_name": "Patient Guides",
    }


def test_create_and_ingest_validation_share_the_same_core_chunking_error(monkeypatch: pytest.MonkeyPatch):
    constraints = context_management_chunking_compatibility.EmbeddingsChunkingConstraints(
        max_input_tokens=256,
        special_tokens_per_input=2,
        safe_chunk_length_max=254,
    )

    monkeypatch.setattr(
        context_management_serialization.platform_repo,
        "get_provider_instance",
        lambda *_args, **_kwargs: {
            "id": "vector-provider-1",
            "provider_key": "weaviate_local",
            "capability_key": "vector_store",
            "enabled": True,
        },
    )
    monkeypatch.setattr(
        "app.services.context_management_vectorization.normalize_knowledge_base_vectorization",
        lambda *_args, **_kwargs: {
            "mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "local-embedding-model",
            "vectorization_json": {
                "embedding_resource": {
                    "id": "local-embedding-model",
                    "provider_resource_id": "local-embedding-model",
                    "display_name": "sentence-transformers/all-MiniLM-L6-v2",
                }
            },
        },
    )
    monkeypatch.setattr(
        context_management_chunking_compatibility,
        "resolve_knowledge_base_chunking_constraints",
        lambda *_args, **_kwargs: constraints,
    )
    monkeypatch.setattr(context_management_shared, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)

    with pytest.raises(PlatformControlPlaneError) as create_exc:
        context_management_serialization._normalize_knowledge_base_payload(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            {
                "slug": "patient-guides",
                "display_name": "Patient Guides",
                "description": "",
                "backing_provider_instance_id": "vector-provider-1",
                "chunking": {
                    "strategy": "fixed_length",
                    "config": {
                        "unit": "tokens",
                        "chunk_length": 300,
                        "chunk_overlap": 60,
                    },
                },
                "vectorization": {
                    "mode": "vanessa_embeddings",
                    "embedding_provider_instance_id": "embedding-provider-1",
                    "embedding_resource_id": "local-embedding-model",
                },
                "schema": {},
            },
            is_create=True,
        )

    with pytest.raises(PlatformControlPlaneError) as ingest_exc:
        context_management_shared._upsert_document_chunks(  # type: ignore[attr-defined]
            "postgresql://ignored",
            object(),
            knowledge_base={
                "id": "kb-primary",
                "index_name": "kb_product_docs",
                "schema_json": {},
                "chunking_strategy": "fixed_length",
                "chunking_config_json": {
                    "unit": "tokens",
                    "chunk_length": 300,
                    "chunk_overlap": 60,
                },
                "embedding_provider_instance_id": "embedding-provider-1",
                "embedding_resource_id": "local-embedding-model",
                "vectorization_json": {
                    "embedding_resource": {
                        "id": "local-embedding-model",
                        "provider_resource_id": "local-embedding-model",
                        "display_name": "sentence-transformers/all-MiniLM-L6-v2",
                    }
                },
            },
            document={
                "id": "doc-1",
                "title": "Patient guide",
                "source_type": "local_directory",
                "source_name": "Patient Guides",
                "source_id": "source-1",
            },
            chunks=["chunk-1"],
        )

    create_core = {
        key: create_exc.value.details[key]
        for key in (
            "embedding_resource_id",
            "embedding_model_display_name",
            "chunk_length",
            "chunk_overlap",
            "max_input_tokens",
            "special_tokens_per_input",
            "safe_chunk_length_max",
        )
    }
    ingest_core = {
        key: ingest_exc.value.details[key]
        for key in (
            "embedding_resource_id",
            "embedding_model_display_name",
            "chunk_length",
            "chunk_overlap",
            "max_input_tokens",
            "special_tokens_per_input",
            "safe_chunk_length_max",
        )
    }

    assert create_exc.value.code == "knowledge_base_chunking_exceeds_embeddings_limit"
    assert ingest_exc.value.code == "knowledge_base_chunking_exceeds_embeddings_limit"
    assert create_core == ingest_core


def test_upsert_document_chunks_propagates_document_metadata_into_chunk_metadata(monkeypatch: pytest.MonkeyPatch):
    captured_upsert: dict[str, object] = {}

    monkeypatch.setattr(context_management_shared, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_shared, "assert_knowledge_base_chunking_compatible", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_shared,
        "_resolve_knowledge_base_vector_adapter",
        lambda *_args, **_kwargs: type(
            "_Adapter",
            (),
            {
                "ensure_index": lambda self, **_kwargs: None,
                "upsert": lambda self, **_kwargs: captured_upsert.update(_kwargs),
            },
        )(),
    )
    monkeypatch.setattr(
        context_management_shared,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.1, 0.2]]},
    )

    context_management_shared._upsert_document_chunks(  # type: ignore[attr-defined]
        "postgresql://ignored",
        object(),
        knowledge_base={
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "schema_json": {"properties": [{"name": "category", "data_type": "text"}]},
        },
        document={
            "id": "doc-1",
            "title": "Architecture Overview",
            "source_type": "manual",
            "source_name": "Docs folder",
            "uri": "https://example.com/overview",
            "metadata_json": {
                "category": "guide",
                "page_count": 7,
                "published": True,
            },
        },
        chunks=["chunk-1"],
    )

    assert captured_upsert["index_name"] == "kb_product_docs"
    assert captured_upsert["documents"] == [
        {
            "id": "doc-1::chunk::0",
            "text": "chunk-1",
            "embedding": [0.1, 0.2],
            "metadata": {
                "category": "guide",
                "page_count": 7,
                "published": True,
                "knowledge_base_id": "kb-primary",
                "document_id": "doc-1",
                "chunk_index": 0,
                "title": "Architecture Overview",
                "source_type": "manual",
                "source_name": "Docs folder",
                "uri": "https://example.com/overview",
            },
        }
    ]


def test_upsert_document_chunks_adds_per_chunk_page_number_metadata(monkeypatch: pytest.MonkeyPatch):
    captured_upsert: dict[str, object] = {}

    monkeypatch.setattr(context_management_shared, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_shared, "assert_knowledge_base_chunking_compatible", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_shared,
        "_resolve_knowledge_base_vector_adapter",
        lambda *_args, **_kwargs: type(
            "_Adapter",
            (),
            {
                "ensure_index": lambda self, **_kwargs: None,
                "upsert": lambda self, **_kwargs: captured_upsert.update(_kwargs),
            },
        )(),
    )
    monkeypatch.setattr(
        context_management_shared,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
    )

    context_management_shared._upsert_document_chunks(  # type: ignore[attr-defined]
        "postgresql://ignored",
        object(),
        knowledge_base={
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "schema_json": {"properties": [{"name": "page_number", "data_type": "int"}]},
        },
        document={
            "id": "doc-1",
            "title": "Architecture Overview",
            "source_type": "upload",
            "source_name": "architecture.pdf",
            "uri": None,
            "metadata_json": {"page_count": 2, "page_number": 999},
        },
        chunks=[
            {"text": "page one chunk", "metadata": {"page_number": 1}},
            {"text": "page two chunk", "metadata": {"page_number": 2}},
        ],
    )

    assert captured_upsert["documents"] == [
        {
            "id": "doc-1::chunk::0",
            "text": "page one chunk",
            "embedding": [0.1, 0.2],
            "metadata": {
                "page_count": 2,
                "page_number": 1,
                "knowledge_base_id": "kb-primary",
                "document_id": "doc-1",
                "chunk_index": 0,
                "title": "Architecture Overview",
                "source_type": "upload",
                "source_name": "architecture.pdf",
                "uri": None,
            },
        },
        {
            "id": "doc-1::chunk::1",
            "text": "page two chunk",
            "embedding": [0.3, 0.4],
            "metadata": {
                "page_count": 2,
                "page_number": 2,
                "knowledge_base_id": "kb-primary",
                "document_id": "doc-1",
                "chunk_index": 1,
                "title": "Architecture Overview",
                "source_type": "upload",
                "source_name": "architecture.pdf",
                "uri": None,
            },
        },
    ]


def test_upsert_document_chunks_keeps_built_in_chunk_metadata_when_document_metadata_conflicts(monkeypatch: pytest.MonkeyPatch):
    captured_upsert: dict[str, object] = {}

    monkeypatch.setattr(context_management_shared, "require_knowledge_base_text_ingestion_supported", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(context_management_shared, "assert_knowledge_base_chunking_compatible", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        context_management_shared,
        "_resolve_knowledge_base_vector_adapter",
        lambda *_args, **_kwargs: type(
            "_Adapter",
            (),
            {
                "ensure_index": lambda self, **_kwargs: None,
                "upsert": lambda self, **_kwargs: captured_upsert.update(_kwargs),
            },
        )(),
    )
    monkeypatch.setattr(
        context_management_shared,
        "embed_knowledge_base_texts",
        lambda *_args, **_kwargs: {"embeddings": [[0.3, 0.4]]},
    )

    context_management_shared._upsert_document_chunks(  # type: ignore[attr-defined]
        "postgresql://ignored",
        object(),
        knowledge_base={
            "id": "kb-primary",
            "index_name": "kb_product_docs",
            "schema_json": {"properties": [{"name": "title", "data_type": "text"}]},
        },
        document={
            "id": "doc-1",
            "title": "Actual title",
            "source_type": "manual",
            "source_name": "Actual source",
            "uri": "https://example.com/actual",
            "metadata_json": {
                "title": "Metadata title",
                "source_name": "Metadata source",
                "chunk_index": 999,
            },
        },
        chunks=["chunk-1"],
    )

    metadata = captured_upsert["documents"][0]["metadata"]  # type: ignore[index]
    assert metadata["title"] == "Actual title"
    assert metadata["source_name"] == "Actual source"
    assert metadata["chunk_index"] == 0
