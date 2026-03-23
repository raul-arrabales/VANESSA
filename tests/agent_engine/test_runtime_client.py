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
    embeddings_provider_key: str = "vllm_embeddings_local",
    embeddings_adapter_kind: str = "openai_compatible_embeddings",
    embeddings_endpoint_url: str = "http://llm:8000",
    embeddings_healthcheck_url: str | None = "http://llm:8000/health",
    embeddings_config: dict[str, object] | None = None,
    vector_provider_key: str = "weaviate_local",
    vector_adapter_kind: str = "weaviate_http",
    vector_endpoint_url: str = "http://weaviate:8080",
    vector_healthcheck_url: str | None = "http://weaviate:8080/v1/.well-known/ready",
    vector_config: dict[str, object] | None = None,
    include_mcp_runtime: bool = False,
    include_sandbox_runtime: bool = False,
) -> dict[str, object]:
    capabilities: dict[str, object] = {
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
            "served_models": [
                {
                    "id": "model.alpha",
                    "name": "Model Alpha",
                    "provider_model_id": "model.alpha",
                },
                {
                    "id": "local-default-model",
                    "name": "Local Default Model",
                    "provider_model_id": "local-default-model",
                },
            ],
            "default_served_model_id": "local-default-model",
            "default_served_model": {
                "id": "local-default-model",
                "name": "Local Default Model",
                "provider_model_id": "local-default-model",
            },
            "binding_config": {},
        },
        "embeddings": {
            "id": "provider-embeddings",
            "slug": "vllm-embeddings-local",
            "provider_key": embeddings_provider_key,
            "display_name": "vLLM embeddings local",
            "description": "desc",
            "adapter_kind": embeddings_adapter_kind,
            "endpoint_url": embeddings_endpoint_url,
            "healthcheck_url": embeddings_healthcheck_url,
            "enabled": True,
            "config": {
                "embeddings_path": "/v1/embeddings",
                "forced_model_id": "local-vllm-embeddings-default",
                **(embeddings_config or {}),
            },
            "served_models": [
                {
                    "id": "local-vllm-embeddings-default",
                    "name": "Local Embeddings Default",
                    "provider_model_id": "local-vllm-embeddings-default",
                }
            ],
            "default_served_model_id": "local-vllm-embeddings-default",
            "default_served_model": {
                "id": "local-vllm-embeddings-default",
                "name": "Local Embeddings Default",
                "provider_model_id": "local-vllm-embeddings-default",
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
        },
    }
    if include_mcp_runtime:
        capabilities["mcp_runtime"] = {
            "id": "provider-mcp",
            "slug": "mcp-gateway-local",
            "provider_key": "mcp_gateway_local",
            "display_name": "MCP Gateway",
            "description": "desc",
            "adapter_kind": "mcp_http",
            "endpoint_url": "http://mcp_gateway:6100",
            "healthcheck_url": "http://mcp_gateway:6100/health",
            "enabled": True,
            "config": {"invoke_path": "/v1/tools/invoke"},
            "binding_config": {},
        }
    if include_sandbox_runtime:
        capabilities["sandbox_execution"] = {
            "id": "provider-sandbox",
            "slug": "sandbox-local",
            "provider_key": "sandbox_local",
            "display_name": "Sandbox",
            "description": "desc",
            "adapter_kind": "sandbox_http",
            "endpoint_url": "http://sandbox:6000",
            "healthcheck_url": "http://sandbox:6000/health",
            "enabled": True,
            "config": {"execute_path": "/v1/execute"},
            "binding_config": {},
        }
    return {
        "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
        "capabilities": capabilities,
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
        "tool_calls": [],
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
        "tool_calls": [],
        "status_code": 200,
        "requested_model": "local-default-model",
    }
    assert seen_payloads == [
        {
            "model": "local-default-model",
            "messages": [{"role": "user", "content": "hello"}],
        }
    ]


def test_openai_compatible_runtime_client_passes_tools_and_normalizes_tool_calls(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {
            "output": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "web_search", "arguments": "{\"query\":\"hello\"}"},
                        }
                    ],
                }
            ]
        }, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    payload = client.chat_completion(
        requested_model="model.alpha",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        tools=[{"type": "function", "function": {"name": "web_search", "parameters": {"type": "object"}}}],
    )

    assert payload["tool_calls"][0]["function"]["name"] == "web_search"
    assert seen_payloads[0]["tools"][0]["function"]["name"] == "web_search"


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
        embedding=[0.1, 0.2],
        top_k=4,
        filters={"tenant": "ops"},
        query_text="hello",
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
                "score_kind": "similarity",
            }
        ],
    }
    assert "nearVector: { vector: [0.1, 0.2] }" in str(seen_payloads[0])
    assert 'where: { path: ["tenant"], operator: Equal, valueText: "ops" }' in str(seen_payloads[0])


def test_weaviate_vector_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_vector_store_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.VectorStoreRuntimeClientError) as exc_info:
        client.query(
            index_name="knowledge_base",
            embedding=[0.1, 0.2],
            top_k=5,
            filters={},
        )

    assert exc_info.value.code == "vector_runtime_timeout"


def test_qdrant_vector_runtime_client_builds_similarity_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {
            "status": "ok",
            "result": [
                {
                    "id": "doc-1",
                    "payload": {
                        "document_id": "doc-1",
                        "text": "retrieved text",
                        "metadata": {"tenant": "ops"},
                    },
                    "score": 0.88,
                }
            ],
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
        embedding=[0.1, 0.2],
        top_k=4,
        filters={"tenant": "ops"},
        query_text="hello",
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
                "score": 0.88,
                "score_kind": "similarity",
            }
        ],
    }
    assert seen_payloads == [
        {
            "vector": [0.1, 0.2],
            "limit": 4,
            "filter": {"must": [{"key": "tenant", "match": {"value": "ops"}}]},
            "with_payload": True,
            "with_vector": False,
        }
    ]


def test_openai_compatible_embeddings_runtime_client_returns_vectors(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_embeddings_runtime_client(_platform_runtime())

    payload = client.embed_texts(texts=["hello"])

    assert payload == {
        "embeddings": [[0.1, 0.2, 0.3]],
        "dimension": 3,
        "status_code": 200,
        "requested_model": "local-vllm-embeddings-default",
    }
    assert seen_payloads == [{"model": "local-vllm-embeddings-default", "input": ["hello"]}]


def test_openai_compatible_embeddings_runtime_client_surfaces_upstream_bad_requests(
    monkeypatch: pytest.MonkeyPatch,
):
    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, payload, headers, timeout_seconds
        return {
            "error": {
                "code": "local_vllm_bad_request",
                "message": "The model does not support Embeddings API",
            }
        }, 400

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_embeddings_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.EmbeddingsRuntimeClientError) as exc_info:
        client.embed_texts(texts=["hello"])

    assert exc_info.value.code == "embeddings_runtime_request_failed"
    assert exc_info.value.status_code == 400
    assert exc_info.value.details["upstream"]["error"]["message"] == "The model does not support Embeddings API"


def test_mcp_tool_runtime_client_invokes_gateway(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"result": {"query": "hello", "results": []}}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_mcp_tool_runtime_client(_platform_runtime(include_mcp_runtime=True))

    payload = client.invoke(tool_name="web_search", arguments={"query": "hello"}, request_metadata={"tool_ref": "tool.web_search"})

    assert payload["result"]["query"] == "hello"
    assert seen_payloads[0]["tool_name"] == "web_search"


def test_sandbox_tool_runtime_client_executes_python(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers, timeout_seconds
        seen_payloads.append(dict(payload or {}))
        return {"stdout": "hi\n", "stderr": "", "result": {"ok": True}, "error": None}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_sandbox_tool_runtime_client(_platform_runtime(include_sandbox_runtime=True))

    payload = client.execute_python(
        code="print('hi')\nresult = {'ok': True}",
        input_payload={"name": "Ada"},
        timeout_seconds=5,
        policy={"network_access": False},
    )

    assert payload["result"] == {"ok": True}
    assert seen_payloads[0]["language"] == "python"
