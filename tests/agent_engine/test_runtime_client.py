from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import runtime_client  # noqa: E402


def _platform_runtime(
    *,
    provider_key: str = "vllm_local",
    request_format: str = "responses_api",
    vector_provider_key: str = "weaviate_local",
    vector_adapter_kind: str = "weaviate_http",
    vector_endpoint_url: str = "http://weaviate:8080",
    vector_healthcheck_url: str | None = "http://weaviate:8080/v1/.well-known/ready",
    vector_config: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
        "capabilities": {
            "llm_inference": {
                "id": "provider-1",
                "slug": "llm-provider",
                "provider_key": provider_key,
                "display_name": "LLM Provider",
                "description": "desc",
                "adapter_kind": "openai_compatible_llm",
                "endpoint_url": "http://llm:8000",
                "healthcheck_url": "http://llm:8000/health",
                "enabled": True,
                "config": {
                    "chat_completion_path": "/v1/chat/completions",
                    "request_format": request_format,
                    "forced_model_id": "local-default-model",
                },
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
                "healthcheck_url": vector_healthcheck_url,
                "enabled": True,
                "config": vector_config or {},
                "binding_config": {},
            }
        },
    }


def test_openai_compatible_runtime_client_supports_vanessa_gateway_payloads(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"output": [{"role": "assistant", "content": [{"type": "text", "text": "gateway reply"}]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    payload = client.chat_completion(
        requested_model="model.alpha",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload == {
        "output_text": "gateway reply",
        "status_code": 200,
        "requested_model": "model.alpha",
    }
    assert seen_payloads == [
        {
            "model": "model.alpha",
            "input": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        }
    ]


def test_openai_compatible_runtime_client_supports_openai_chat_responses(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"choices": [{"message": {"role": "assistant", "content": "llama.cpp reply"}}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(
        _platform_runtime(provider_key="llama_cpp_local", request_format="openai_chat")
    )

    payload = client.chat_completion(
        requested_model=None,
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload == {
        "output_text": "llama.cpp reply",
        "status_code": 200,
        "requested_model": "local-default-model",
    }
    assert seen_payloads == [
        {
            "model": "local-default-model",
            "messages": [{"role": "user", "content": "hello"}],
        }
    ]


def test_openai_compatible_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.LlmRuntimeClientError) as exc_info:
        client.chat_completion(
            requested_model="model.alpha",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

    assert exc_info.value.code == "runtime_unreachable"


def test_weaviate_vector_runtime_client_builds_bm25_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {
            "data": {
                "Get": {
                    "KnowledgeBase": [
                        {
                            "document_id": "doc-1",
                            "text": "retrieved text",
                            "metadata_json": '{"tenant":"ops"}',
                            "_additional": {"id": "uuid-1", "score": 7.5},
                        }
                    ]
                }
            }
        }, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_vector_store_runtime_client(_platform_runtime())

    payload = client.query(
        index_name="knowledge_base",
        query_text="hello",
        top_k=4,
        filters={"tenant": "ops"},
    )

    assert payload == {
        "index": "knowledge_base",
        "query": "hello",
        "top_k": 4,
        "results": [
            {
                "id": "doc-1",
                "text": "retrieved text",
                "metadata": {"tenant": "ops"},
                "score": 7.5,
                "score_kind": "bm25",
            }
        ],
    }
    assert 'bm25: { query: "hello", properties: ["text"] }' in str(seen_payloads[0])
    assert 'where: { path: ["tenant"], operator: Equal, valueText: "ops" }' in str(seen_payloads[0])


def test_weaviate_vector_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_vector_store_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.VectorStoreRuntimeClientError) as exc_info:
        client.query(
            index_name="knowledge_base",
            query_text="hello",
            top_k=5,
            filters={},
        )

    assert exc_info.value.code == "vector_runtime_timeout"


def test_qdrant_vector_runtime_client_builds_scroll_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {
            "status": "ok",
            "result": {
                "points": [
                    {
                        "id": "doc-1",
                        "payload": {
                            "document_id": "doc-1",
                            "text": "retrieved text",
                            "metadata": {"tenant": "ops"},
                        },
                    }
                ]
            },
        }, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_vector_store_runtime_client(
        _platform_runtime(
            vector_provider_key="qdrant_local",
            vector_adapter_kind="qdrant_http",
            vector_endpoint_url="http://qdrant:6333",
            vector_healthcheck_url="http://qdrant:6333/healthz",
        )
    )

    payload = client.query(
        index_name="knowledge_base",
        query_text="hello",
        top_k=4,
        filters={"tenant": "ops"},
    )

    assert payload == {
        "index": "knowledge_base",
        "query": "hello",
        "top_k": 4,
        "results": [
            {
                "id": "doc-1",
                "text": "retrieved text",
                "metadata": {"tenant": "ops"},
                "score": 1.0,
                "score_kind": "text_match",
            }
        ],
    }
    assert seen_payloads == [
        {
            "limit": 4,
            "filter": {
                "must": [
                    {"key": "tenant", "match": {"value": "ops"}},
                    {"key": "text", "match": {"text": "hello"}},
                ]
            },
            "with_payload": True,
            "with_vector": False,
        }
    ]
