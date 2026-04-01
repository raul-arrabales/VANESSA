from __future__ import annotations

import pytest

from app.services import platform_adapters, vector_store_service  # noqa: E402
from app.services.platform_types import PlatformControlPlaneError, ProviderBinding  # noqa: E402


def _binding() -> ProviderBinding:
    return ProviderBinding(
        capability_key="vector_store",
        provider_instance_id="provider-1",
        provider_slug="weaviate-local",
        provider_key="weaviate_local",
        provider_display_name="Weaviate local",
        provider_description="desc",
        endpoint_url="http://weaviate:8080",
        healthcheck_url="http://weaviate:8080/v1/.well-known/ready",
        enabled=True,
        adapter_kind="weaviate_http",
        config={},
        binding_config={},
        deployment_profile_id="deployment-1",
        deployment_profile_slug="local-default",
        deployment_profile_display_name="Local Default",
    )


def _qdrant_binding() -> ProviderBinding:
    return ProviderBinding(
        capability_key="vector_store",
        provider_instance_id="provider-2",
        provider_slug="qdrant-local",
        provider_key="qdrant_local",
        provider_display_name="Qdrant local",
        provider_description="desc",
        endpoint_url="http://qdrant:6333",
        healthcheck_url="http://qdrant:6333/healthz",
        enabled=True,
        adapter_kind="qdrant_http",
        config={"default_vector_size": 2, "distance": "Cosine"},
        binding_config={},
        deployment_profile_id="deployment-2",
        deployment_profile_slug="local-qdrant",
        deployment_profile_display_name="Local Qdrant",
    )


def test_ensure_vector_index_validates_and_delegates(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class _Adapter:
        def ensure_index(self, *, index_name: str, schema: dict[str, object]) -> dict[str, object]:
            calls.append((index_name, schema))
            return {"index": {"name": index_name, "created": True, "status": "ready"}}

    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: _Adapter())

    payload = vector_store_service.ensure_vector_index(
        "ignored",
        object(),  # type: ignore[arg-type]
        {
            "index": "knowledge_base",
            "schema": {"properties": [{"name": "category", "data_type": "text"}]},
        },
    )

    assert calls == [("knowledge_base", {"properties": [{"name": "category", "data_type": "text"}]})]
    assert payload["index"]["created"] is True


def test_upsert_vector_documents_rejects_nested_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: object())

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        vector_store_service.upsert_vector_documents(
            "ignored",
            object(),  # type: ignore[arg-type]
            {
                "index": "knowledge_base",
                "documents": [{"id": "doc-1", "text": "hello", "metadata": {"tags": ["a"]}}],
            },
        )

    assert exc_info.value.code == "invalid_metadata_value"


def test_query_vector_documents_requires_exactly_one_query_input(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: object())

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        vector_store_service.query_vector_documents(
            "ignored",
            object(),  # type: ignore[arg-type]
            {
                "index": "knowledge_base",
                "query_text": "hello",
                "embedding": [0.1, 0.2],
            },
        )

    assert exc_info.value.code == "invalid_query_input"


def test_query_vector_documents_normalizes_payload_and_delegates(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, object]] = []

    class _Adapter:
        def query(
            self,
            *,
            index_name: str,
            query_text: str | None,
            embedding: list[float] | None,
            top_k: int,
            filters: dict[str, object],
        ) -> dict[str, object]:
            calls.append(
                {
                    "index_name": index_name,
                    "query_text": query_text,
                    "embedding": embedding,
                    "top_k": top_k,
                    "filters": filters,
                }
            )
            return {"index": index_name, "results": []}

    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: _Adapter())

    payload = vector_store_service.query_vector_documents(
        "ignored",
        object(),  # type: ignore[arg-type]
        {
            "index": "knowledge_base",
            "embedding": [0.1, 2, 3.5],
            "top_k": "7",
            "filters": {"tenant": "ops", "published": True},
        },
    )

    assert calls == [
        {
            "index_name": "knowledge_base",
            "query_text": None,
            "embedding": [0.1, 2.0, 3.5],
            "top_k": 7,
            "filters": {"tenant": "ops", "published": True},
        }
    ]
    assert payload == {"index": "knowledge_base", "results": []}


def test_query_vector_documents_embeds_query_text_before_delegate(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, object]] = []

    class _Adapter:
        def query(
            self,
            *,
            index_name: str,
            query_text: str | None,
            embedding: list[float] | None,
            top_k: int,
            filters: dict[str, object],
        ) -> dict[str, object]:
            calls.append(
                {
                    "index_name": index_name,
                    "query_text": query_text,
                    "embedding": embedding,
                    "top_k": top_k,
                    "filters": filters,
                }
            )
            return {"index": index_name, "results": []}

    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: _Adapter())
    monkeypatch.setattr(
        vector_store_service,
        "embed_text_inputs",
        lambda _db, _config, texts: {
            "provider": {"slug": "vllm-embeddings-local"},
            "count": len(texts),
            "dimension": 2,
            "embeddings": [[0.1, 0.2]],
        },
    )

    payload = vector_store_service.query_vector_documents(
        "ignored",
        object(),  # type: ignore[arg-type]
        {
            "index": "knowledge_base",
            "query_text": "hello",
            "top_k": 3,
        },
    )

    assert payload == {"index": "knowledge_base", "results": []}
    assert calls == [
        {
            "index_name": "knowledge_base",
            "query_text": None,
            "embedding": [0.1, 0.2],
            "top_k": 3,
            "filters": {},
        }
    ]


def test_upsert_vector_documents_generates_embeddings_for_missing_documents(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, object]] = []

    class _Adapter:
        def upsert(self, *, index_name: str, documents: list[dict[str, object]]) -> dict[str, object]:
            calls.append({"index_name": index_name, "documents": documents})
            return {"index": index_name, "count": len(documents), "documents": documents}

    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: _Adapter())
    monkeypatch.setattr(
        vector_store_service,
        "embed_text_inputs",
        lambda _db, _config, texts: {
            "provider": {"slug": "vllm-embeddings-local"},
            "count": len(texts),
            "dimension": 2,
            "embeddings": [[0.1, 0.2] for _ in texts],
        },
    )

    payload = vector_store_service.upsert_vector_documents(
        "ignored",
        object(),  # type: ignore[arg-type]
        {
            "index": "knowledge_base",
            "documents": [
                {"id": "doc-1", "text": "hello"},
                {"id": "doc-2", "text": "world", "embedding": [0.9, 1.1]},
            ],
        },
    )

    assert payload["count"] == 2
    assert calls == [
        {
            "index_name": "knowledge_base",
            "documents": [
                {"id": "doc-1", "text": "hello", "metadata": {}, "embedding": [0.1, 0.2]},
                {"id": "doc-2", "text": "world", "metadata": {}, "embedding": [0.9, 1.1]},
            ],
        }
    ]


def test_delete_vector_documents_requires_non_empty_ids(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(vector_store_service, "resolve_vector_store_adapter", lambda _db, _config: object())

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        vector_store_service.delete_vector_documents(
            "ignored",
            object(),  # type: ignore[arg-type]
            {"index": "knowledge_base", "ids": []},
        )

    assert exc_info.value.code == "invalid_ids"


def test_weaviate_vector_store_adapter_ensure_index_creates_schema(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        calls.append((url, method, payload))
        if url.endswith("/v1/schema/KnowledgeBase"):
            return {"error": "not_found"}, 404
        if url.endswith("/v1/schema"):
            return {"class": "KnowledgeBase"}, 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    payload = adapter.ensure_index(
        index_name="knowledge_base",
        schema={"properties": [{"name": "category", "data_type": "text"}]},
    )

    assert payload == {
        "index": {
            "name": "knowledge_base",
            "provider": "weaviate-local",
            "status": "ready",
            "created": True,
        }
    }
    assert calls == [
        ("http://weaviate:8080/v1/schema/KnowledgeBase", "GET", None),
        (
            "http://weaviate:8080/v1/schema",
            "POST",
            {
                "class": "KnowledgeBase",
                "vectorizer": "none",
                "properties": [
                    {"name": "document_id", "dataType": ["text"]},
                    {"name": "text", "dataType": ["text"]},
                    {"name": "metadata_json", "dataType": ["text"]},
                    {"name": "category", "dataType": ["text"]},
                ],
            },
        ),
    ]


def test_weaviate_vector_store_adapter_upsert_returns_normalized_documents(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        calls.append((url, method, payload))
        if url.endswith("/v1/schema/KnowledgeBase"):
            return {"class": "KnowledgeBase"}, 200
        if url.endswith("/v1/batch/objects"):
            return {"objects": [{"result": {"errors": None}}]}, 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    payload = adapter.upsert(
        index_name="knowledge_base",
        documents=[
            {
                "id": "doc-1",
                "text": "hello",
                "metadata": {"category": "ops"},
                "embedding": [0.1, 0.2],
            }
        ],
    )

    assert payload == {
        "index": "knowledge_base",
        "count": 1,
        "documents": [{"id": "doc-1", "status": "upserted"}],
    }
    assert calls[1][0] == "http://weaviate:8080/v1/batch/objects"
    assert calls[1][2] == {
        "objects": [
            {
                "class": "KnowledgeBase",
                "id": platform_adapters._weaviate_object_uuid("knowledge_base", "doc-1"),
                "properties": {
                    "document_id": "doc-1",
                    "text": "hello",
                    "metadata_json": '{"category": "ops"}',
                    "category": "ops",
                },
                "vector": [0.1, 0.2],
            }
        ]
    }


def test_weaviate_vector_store_adapter_upsert_accepts_list_shaped_batch_response(monkeypatch: pytest.MonkeyPatch):
    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        if url.endswith("/v1/schema/KnowledgeBase"):
            return {"class": "KnowledgeBase"}, 200
        if url.endswith("/v1/batch/objects"):
            return [{"result": {"errors": None}}], 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    payload = adapter.upsert(
        index_name="knowledge_base",
        documents=[{"id": "doc-1", "text": "hello", "metadata": {}, "embedding": [0.1, 0.2]}],
    )

    assert payload == {
        "index": "knowledge_base",
        "count": 1,
        "documents": [{"id": "doc-1", "status": "upserted"}],
    }


def test_weaviate_vector_store_adapter_upsert_raises_on_list_shaped_batch_errors(monkeypatch: pytest.MonkeyPatch):
    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        if url.endswith("/v1/schema/KnowledgeBase"):
            return {"class": "KnowledgeBase"}, 200
        if url.endswith("/v1/batch/objects"):
            return [{"result": {"errors": [{"message": "vector write failed"}]}}], 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        adapter.upsert(
            index_name="knowledge_base",
            documents=[{"id": "doc-1", "text": "hello", "metadata": {}, "embedding": [0.1, 0.2]}],
        )

    assert exc_info.value.code == "vector_upsert_failed"


def test_weaviate_vector_store_adapter_upsert_raises_on_unexpected_batch_response_shape(
    monkeypatch: pytest.MonkeyPatch,
):
    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        if url.endswith("/v1/schema/KnowledgeBase"):
            return {"class": "KnowledgeBase"}, 200
        if url.endswith("/v1/batch/objects"):
            return {"status": "ok"}, 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    with pytest.raises(PlatformControlPlaneError) as exc_info:
        adapter.upsert(
            index_name="knowledge_base",
            documents=[{"id": "doc-1", "text": "hello", "metadata": {}, "embedding": [0.1, 0.2]}],
        )

    assert exc_info.value.code == "vector_upsert_failed"


def test_weaviate_vector_store_adapter_query_supports_embedding_and_bm25(monkeypatch: pytest.MonkeyPatch):
    requests: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        requests.append({"url": url, "method": method, "payload": payload})
        if len(requests) == 1:
            return {
                "data": {
                    "Get": {
                        "KnowledgeBase": [
                            {
                                "document_id": "doc-1",
                                "text": "hello",
                                "metadata_json": '{"category": "ops"}',
                                "_additional": {"id": "uuid-1", "distance": 0.12},
                            }
                        ]
                    }
                }
            }, 200
        return {
            "data": {
                "Get": {
                    "KnowledgeBase": [
                        {
                            "document_id": "doc-2",
                            "text": "world",
                            "metadata_json": '{"category": "docs"}',
                            "_additional": {"id": "uuid-2", "score": 7.5},
                        }
                    ]
                }
            }
        }, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    embedding_result = adapter.query(
        index_name="knowledge_base",
        query_text=None,
        embedding=[0.1, 0.2],
        top_k=3,
        filters={"category": "ops"},
    )
    text_result = adapter.query(
        index_name="knowledge_base",
        query_text="hello",
        embedding=None,
        top_k=2,
        filters={},
    )

    assert embedding_result == {
        "index": "knowledge_base",
        "results": [
            {
                "id": "doc-1",
                "text": "hello",
                "metadata": {"category": "ops"},
                "score": 0.12,
                "score_kind": "distance",
            }
        ],
    }
    assert text_result == {
        "index": "knowledge_base",
        "results": [
            {
                "id": "doc-2",
                "text": "world",
                "metadata": {"category": "docs"},
                "score": 7.5,
                "score_kind": "bm25",
            }
        ],
    }
    embedding_query = str((requests[0]["payload"] or {}).get("query"))
    text_query = str((requests[1]["payload"] or {}).get("query"))
    assert 'nearVector: { vector: [0.1,0.2] }' in embedding_query
    assert 'where: { path: ["category"], operator: Equal, valueText: "ops" }' in embedding_query
    assert embedding_query.count("{") == embedding_query.count("}")
    assert 'bm25: { query: "hello", properties: ["text"] }' in text_query
    assert text_query.count("{") == text_query.count("}")


def test_weaviate_vector_store_adapter_delete_returns_deleted_ids(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del payload, headers, timeout_seconds
        calls.append((url, method))
        if url.endswith(platform_adapters._weaviate_object_uuid("knowledge_base", "doc-1")):
            return {}, 204
        if url.endswith(platform_adapters._weaviate_object_uuid("knowledge_base", "doc-2")):
            return {"error": "not_found"}, 404
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.WeaviateVectorStoreAdapter(_binding())

    payload = adapter.delete(index_name="knowledge_base", ids=["doc-1", "doc-2"])

    assert payload == {
        "index": "knowledge_base",
        "count": 1,
        "deleted_ids": ["doc-1"],
    }
    assert calls == [
        (
            "http://weaviate:8080/v1/objects/KnowledgeBase/"
            + platform_adapters._weaviate_object_uuid("knowledge_base", "doc-1"),
            "DELETE",
        ),
        (
            "http://weaviate:8080/v1/objects/KnowledgeBase/"
            + platform_adapters._weaviate_object_uuid("knowledge_base", "doc-2"),
            "DELETE",
        ),
    ]


def test_qdrant_vector_store_adapter_ensure_index_creates_collection_and_text_index(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        calls.append((url, method, payload))
        if url.endswith("/collections/knowledge_base"):
            if method == "GET":
                return {"status": "not_found"}, 404
            return {"status": "ok", "result": True}, 200
        if url.endswith("/collections/knowledge_base/index"):
            return {"status": "ok", "result": True}, 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.QdrantVectorStoreAdapter(_qdrant_binding())

    payload = adapter.ensure_index(index_name="knowledge_base", schema={"properties": [{"name": "tenant", "data_type": "text"}]})

    assert payload == {
        "index": {
            "name": "knowledge_base",
            "provider": "qdrant-local",
            "status": "ready",
            "created": True,
        }
    }
    assert calls == [
        ("http://qdrant:6333/collections/knowledge_base", "GET", None),
        (
            "http://qdrant:6333/collections/knowledge_base",
            "PUT",
            {"vectors": {"size": 2, "distance": "Cosine"}},
        ),
        (
            "http://qdrant:6333/collections/knowledge_base/index",
            "PUT",
            {
                "field_name": "text",
                "field_schema": {
                    "type": "text",
                    "tokenizer": "word",
                    "lowercase": True,
                    "phrase_matching": True,
                },
            },
        ),
        (
            "http://qdrant:6333/collections/knowledge_base/index",
            "PUT",
            {"field_name": "tenant", "field_schema": "keyword"},
        ),
    ]


def test_qdrant_vector_store_adapter_upsert_and_query_return_normalized_documents(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        calls.append((url, method, payload))
        if url.endswith("/collections/knowledge_base") and method == "GET":
            return {"status": "ok", "result": {"status": "green"}}, 200
        if url.endswith("/collections/knowledge_base/index"):
            return {"status": "ok", "result": True}, 200
        if url.endswith("/collections/knowledge_base/points") and method == "PUT":
            return {"status": "ok", "result": {"status": "acknowledged"}}, 200
        if url.endswith("/collections/knowledge_base/points/search"):
            return {
                "status": "ok",
                "result": [
                    {
                        "id": "doc-1",
                        "score": 0.87,
                        "payload": {
                            "document_id": "doc-1",
                            "text": "hello",
                            "metadata": {"tenant": "ops"},
                        },
                    }
                ],
            }, 200
        if url.endswith("/collections/knowledge_base/points/scroll"):
            return {
                "status": "ok",
                "result": {
                    "points": [
                        {
                            "id": "doc-1",
                            "payload": {
                                "document_id": "doc-1",
                                "text": "hello",
                                "metadata": {"tenant": "ops"},
                            },
                        }
                    ]
                },
            }, 200
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.QdrantVectorStoreAdapter(_qdrant_binding())

    upsert_payload = adapter.upsert(
        index_name="knowledge_base",
        documents=[{"id": "doc-1", "text": "hello", "metadata": {"tenant": "ops"}, "embedding": [0.1, 0.2]}],
    )
    vector_query_payload = adapter.query(
        index_name="knowledge_base",
        query_text=None,
        embedding=[0.1, 0.2],
        top_k=3,
        filters={"tenant": "ops"},
    )
    text_query_payload = adapter.query(
        index_name="knowledge_base",
        query_text="hello",
        embedding=None,
        top_k=2,
        filters={"tenant": "ops"},
    )

    assert upsert_payload == {
        "index": "knowledge_base",
        "count": 1,
        "documents": [{"id": "doc-1", "status": "upserted"}],
    }
    assert vector_query_payload == {
        "index": "knowledge_base",
        "results": [
            {
                "id": "doc-1",
                "text": "hello",
                "metadata": {"tenant": "ops"},
                "score": 0.87,
                "score_kind": "similarity",
            }
        ],
    }
    assert text_query_payload == {
        "index": "knowledge_base",
        "results": [
            {
                "id": "doc-1",
                "text": "hello",
                "metadata": {"tenant": "ops"},
                "score": 1.0,
                "score_kind": "text_match",
            }
        ],
    }
    assert calls[2] == (
        "http://qdrant:6333/collections/knowledge_base/points",
        "PUT",
        {
            "points": [
                {
                    "id": "doc-1",
                    "vector": [0.1, 0.2],
                    "payload": {
                        "document_id": "doc-1",
                        "text": "hello",
                        "metadata": {"tenant": "ops"},
                        "tenant": "ops",
                    },
                }
            ]
        },
    )
    assert calls[3][2] == {
        "vector": [0.1, 0.2],
        "limit": 3,
        "filter": {"must": [{"key": "tenant", "match": {"value": "ops"}}]},
        "with_payload": True,
        "with_vector": False,
    }
    assert calls[4][2] == {
        "limit": 2,
        "filter": {
            "must": [
                {"key": "tenant", "match": {"value": "ops"}},
                {"key": "text", "match": {"text": "hello"}},
            ]
        },
        "with_payload": True,
        "with_vector": False,
    }


def test_qdrant_vector_store_adapter_delete_returns_deleted_ids(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=2.0):
        del headers, timeout_seconds
        calls.append((url, method, payload))
        return {"status": "ok", "result": {"status": "acknowledged"}}, 200

    monkeypatch.setattr(platform_adapters, "http_json_request", _request)
    adapter = platform_adapters.QdrantVectorStoreAdapter(_qdrant_binding())

    payload = adapter.delete(index_name="knowledge_base", ids=["doc-1", "doc-2"])

    assert payload == {
        "index": "knowledge_base",
        "count": 2,
        "deleted_ids": ["doc-1", "doc-2"],
    }
    assert calls == [
        (
            "http://qdrant:6333/collections/knowledge_base/points/delete",
            "POST",
            {"points": ["doc-1", "doc-2"]},
        )
    ]
