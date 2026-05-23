from __future__ import annotations

from json import loads
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_engine.app.services import runtime_client  # noqa: E402
from agent_engine.app.services.runtime_clients import transport as runtime_transport  # noqa: E402


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
    include_image_analysis_runtime: bool = False,
    include_image_generation_runtime: bool = False,
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
                "request_timeout_seconds": 60,
            },
            "resources": [
                {
                    "id": "model.alpha",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "model.alpha",
                    "provider_resource_id": "model.alpha",
                    "display_name": "Model Alpha",
                },
                {
                    "id": "local-default-model",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "local-default-model",
                    "provider_resource_id": "local-default-model",
                    "display_name": "Local Default Model",
                },
            ],
            "default_resource_id": "local-default-model",
            "default_resource": {
                "id": "local-default-model",
                "resource_kind": "model",
                "ref_type": "managed_model",
                "managed_model_id": "local-default-model",
                "provider_resource_id": "local-default-model",
                "display_name": "Local Default Model",
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
                "request_timeout_seconds": 60,
                **(embeddings_config or {}),
            },
            "resources": [
                {
                    "id": "local-vllm-embeddings-default",
                    "resource_kind": "model",
                    "ref_type": "managed_model",
                    "managed_model_id": "local-vllm-embeddings-default",
                    "provider_resource_id": "local-vllm-embeddings-default",
                    "display_name": "Local Embeddings Default",
                }
            ],
            "default_resource_id": "local-vllm-embeddings-default",
            "default_resource": {
                "id": "local-vllm-embeddings-default",
                "resource_kind": "model",
                "ref_type": "managed_model",
                "managed_model_id": "local-vllm-embeddings-default",
                "provider_resource_id": "local-vllm-embeddings-default",
                "display_name": "Local Embeddings Default",
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
            "endpoint_url": "http://mcp_gateway:8080",
            "healthcheck_url": "http://mcp_gateway:8080/health",
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
    if include_image_analysis_runtime:
        capabilities["image_analysis"] = {
            "id": "provider-image",
            "slug": "image-analysis-local",
            "provider_key": "image_analysis_local",
            "display_name": "Image analysis",
            "description": "desc",
            "adapter_kind": "image_analysis_http",
            "endpoint_url": "http://image_analysis:8090",
            "healthcheck_url": "http://image_analysis:8090/health",
            "enabled": True,
            "config": {"analyze_path": "/v1/analyze", "request_timeout_seconds": 30},
            "resources": [
                {"id": "plate-detector", "metadata": {"task_key": "image_plate_detection"}},
                {"id": "plate-ocr", "metadata": {"task_key": "image_plate_ocr"}},
                {"id": "object-detector", "metadata": {"task_key": "object_detection"}},
                {"id": "captioner", "metadata": {"task_key": "image_captioning"}},
            ],
            "default_resource_id": None,
            "resource_policy": {
                "selection_mode": "task_defaults",
                "task_defaults": {
                    "plate_detector": "plate-detector",
                    "plate_ocr": "plate-ocr",
                    "object_detector": "object-detector",
                    "captioner": "captioner",
                },
            },
            "binding_config": {},
        }
    if include_image_generation_runtime:
        capabilities["image_generation"] = {
            "id": "provider-image-generation",
            "slug": "image-generation-local",
            "provider_key": "image_generation_local",
            "display_name": "Image generation",
            "description": "desc",
            "adapter_kind": "image_generation_http",
            "endpoint_url": "http://image_generation:8094",
            "healthcheck_url": "http://image_generation:8094/health",
            "enabled": True,
            "config": {"generate_path": "/v1/generate", "request_timeout_seconds": 45},
            "resources": [
                {"id": "generator", "metadata": {"task_key": "image_text_to_image"}},
                {"id": "plate-logo-processor", "metadata": {"task_key": "image_plate_logo_replacement"}},
            ],
            "default_resource_id": None,
            "resource_policy": {
                "selection_mode": "task_defaults",
                "task_defaults": {
                    "generator": "generator",
                    "plate_logo_processor": "plate-logo-processor",
                },
            },
            "binding_config": {},
        }
    return {
        "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
        "capabilities": capabilities,
    }


def test_openai_compatible_runtime_client_supports_vanessa_gateway_payloads(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []
    seen_timeouts: list[float] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers
        seen_payloads.append(dict(payload or {}))
        seen_timeouts.append(timeout_seconds)
        return {"output": [{"role": "assistant", "content": [{"type": "text", "text": "gateway reply"}]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    runtime = _platform_runtime()
    runtime["capabilities"]["llm_inference"]["config"].update(
        {
            "request_options": {
                "service_tier": "priority",
                "prompt_cache_key": "agent-chat",
                "prompt_cache_retention": "24h",
                "reasoning_effort": "low",
            },
            "stream_options": {"include_usage": True},
        }
    )
    client = runtime_client.build_llm_runtime_client(runtime)

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
            "service_tier": "priority",
            "prompt_cache_key": "agent-chat",
            "prompt_cache_retention": "24h",
            "reasoning": {"effort": "low"},
        }
    ]
    assert seen_timeouts == [60.0]


def test_openai_compatible_runtime_client_sends_runtime_secret_headers(monkeypatch: pytest.MonkeyPatch):
    seen_headers: list[dict[str, str]] = []
    runtime = _platform_runtime(provider_key="openai_compatible_cloud_llm")
    llm = runtime["capabilities"]["llm_inference"]
    assert isinstance(llm, dict)
    config = llm["config"]
    assert isinstance(config, dict)
    config["secret_refs"] = {"api_key": "sk-runtime"}

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, payload, timeout_seconds
        seen_headers.append(dict(headers or {}))
        return {"output": [{"role": "assistant", "content": [{"type": "text", "text": "cloud reply"}]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(runtime)

    payload = client.chat_completion(
        requested_model="model.alpha",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload["output_text"] == "cloud reply"
    assert seen_headers == [{"Authorization": "Bearer sk-runtime"}]


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


def test_openai_compatible_runtime_client_uses_loaded_runtime_model_id_for_matching_local_binding(
    monkeypatch: pytest.MonkeyPatch,
):
    seen_payloads: list[dict[str, object]] = []
    runtime = _platform_runtime()
    llm = runtime["capabilities"]["llm_inference"]
    assert isinstance(llm, dict)
    llm["config"] = {
        **dict(llm.get("config") or {}),
        "loaded_runtime_model_id": "loaded",
        "loaded_local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
    }
    llm["resources"] = [
        {
            "id": "Qwen--Qwen2.5-0.5B-Instruct",
            "resource_kind": "model",
            "ref_type": "managed_model",
            "managed_model_id": "Qwen--Qwen2.5-0.5B-Instruct",
            "provider_resource_id": None,
            "display_name": "Qwen2.5-0.5B-Instruct",
            "local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
            "source_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "metadata": {
                "provider_model_id": None,
                "local_path": "/models/llm/Qwen--Qwen2.5-0.5B-Instruct",
                "source_id": "Qwen/Qwen2.5-0.5B-Instruct",
            },
        }
    ]
    llm["default_resource_id"] = "Qwen--Qwen2.5-0.5B-Instruct"
    llm["default_resource"] = dict(llm["resources"][0])

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del headers, timeout_seconds
        if url.endswith("/v1/models"):
            return {"data": [{"id": "loaded"}]}, 200
        seen_payloads.append(dict(payload or {}))
        return {"output": [{"role": "assistant", "content": [{"type": "text", "text": "llm reply"}]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_llm_runtime_client(runtime)

    payload = client.chat_completion(
        requested_model="Qwen--Qwen2.5-0.5B-Instruct",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    )

    assert payload["requested_model"] == "Qwen--Qwen2.5-0.5B-Instruct"
    assert seen_payloads == [
        {
            "model": "loaded",
            "input": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
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


def test_openai_compatible_runtime_client_streams_vanessa_gateway_events(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    class FakeResponse:
        status = 200

        def __init__(self):
            self._lines = iter(
                [
                    b"event: delta\n",
                    b"data: {\"text\":\"Hel\"}\n",
                    b"\n",
                    b"event: delta\n",
                    b"data: {\"text\":\"lo\"}\n",
                    b"\n",
                    b"event: complete\n",
                    b"data: {\"response\":{\"output\":[{\"content\":[{\"type\":\"text\",\"text\":\"Hello\"}]}]}}\n",
                    b"\n",
                ]
            )

        def readline(self):
            return next(self._lines, b"")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _request(*_args, data=None, **_kwargs):
        seen_payloads.append(loads(data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(runtime_transport._HTTP_CLIENT, "request", _request)
    runtime = _platform_runtime()
    runtime["capabilities"]["llm_inference"]["config"].update(
        {
            "request_options": {
                "service_tier": "priority",
                "prompt_cache_key": "agent-chat",
                "prompt_cache_retention": "24h",
                "reasoning_effort": "low",
            },
            "stream_options": {"include_usage": True},
        }
    )
    client = runtime_client.build_llm_runtime_client(runtime)

    events = list(client.chat_completion_stream(
        requested_model="model.alpha",
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    ))

    assert seen_payloads[0]["stream"] is True
    assert seen_payloads[0]["service_tier"] == "priority"
    assert seen_payloads[0]["prompt_cache_key"] == "agent-chat"
    assert seen_payloads[0]["prompt_cache_retention"] == "24h"
    assert seen_payloads[0]["reasoning"] == {"effort": "low"}
    assert seen_payloads[0]["stream_options"] == {"include_usage": True}
    assert [event["type"] for event in events] == ["transport", "delta", "delta", "complete"]
    assert [event.get("text") for event in events if event["type"] == "delta"] == ["Hel", "lo"]
    assert events[-1]["requested_model"] == "model.alpha"


def test_openai_compatible_runtime_client_streams_openai_chat_chunks(monkeypatch: pytest.MonkeyPatch):
    class FakeResponse:
        status = 200

        def __init__(self):
            self._lines = iter(
                [
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n",
                    b"\n",
                    b"data: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}]}\n",
                    b"\n",
                    b"data: [DONE]\n",
                    b"\n",
                ]
            )

        def readline(self):
            return next(self._lines, b"")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(runtime_transport._HTTP_CLIENT, "request", lambda *_args, **_kwargs: FakeResponse())
    client = runtime_client.build_llm_runtime_client(
        _platform_runtime(provider_key="llama_cpp_local", request_format="openai_chat")
    )

    events = list(client.chat_completion_stream(
        requested_model=None,
        messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
    ))

    assert [event["type"] for event in events] == ["transport", "delta", "delta", "complete"]
    assert events[-1]["response"]["output"][0]["content"][0]["text"] == "Hello"


def test_openai_compatible_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_llm_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.LlmRuntimeClientError) as exc_info:
        client.chat_completion(
            requested_model="model.alpha",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

    assert exc_info.value.code == "runtime_unreachable"


def test_weaviate_vector_runtime_client_builds_semantic_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
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
                            "_additional": {"id": "uuid-1", "distance": 0.25},
                        }
                    ]
                }
            }
        }, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_vector_store_runtime_client(_platform_runtime())

    payload = client.query(
        index_name="knowledge_base",
        search_method="semantic",
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
                "score": 0.25,
                "score_kind": "distance",
            }
        ],
    }
    assert str(seen_payloads[0]["query"]).count("{") == str(seen_payloads[0]["query"]).count("}")
    assert "nearVector: { vector: [0.1, 0.2] }" in str(seen_payloads[0])
    assert 'where: { path: ["tenant"], operator: Equal, valueText: "ops" }' in str(seen_payloads[0])


def test_weaviate_vector_runtime_client_builds_keyword_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
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
        search_method="keyword",
        embedding=None,
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
                "score_kind": "bm25",
            }
        ],
    }
    assert 'bm25: { query: "hello", properties: ["text"] }' in str(seen_payloads[0])


def test_weaviate_vector_runtime_client_maps_transport_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runtime_client, "http_json_request", lambda *args, **kwargs: (None, 504))
    client = runtime_client.build_vector_store_runtime_client(_platform_runtime())

    with pytest.raises(runtime_client.VectorStoreRuntimeClientError) as exc_info:
        client.query(
            index_name="knowledge_base",
            search_method="semantic",
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
        search_method="semantic",
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


def test_qdrant_vector_runtime_client_builds_keyword_query_and_normalizes_results(monkeypatch: pytest.MonkeyPatch):
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
                        "score": 1.0,
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
        search_method="keyword",
        embedding=None,
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


def test_openai_compatible_embeddings_runtime_client_returns_vectors(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []
    seen_timeouts: list[float] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del url, method, headers
        seen_payloads.append(dict(payload or {}))
        seen_timeouts.append(timeout_seconds)
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
    assert seen_timeouts == [60.0]


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


def test_openai_compatible_embeddings_runtime_client_resolves_local_model_when_provider_model_id_is_null(
    monkeypatch: pytest.MonkeyPatch,
):
    seen_requests: list[tuple[str, dict[str, object] | None]] = []
    runtime = _platform_runtime()
    embeddings = runtime["capabilities"]["embeddings"]
    assert isinstance(embeddings, dict)
    embeddings["resources"] = [
        {
            "id": "sentence-transformers--all-MiniLM-L6-v2",
            "resource_kind": "model",
            "ref_type": "managed_model",
            "managed_model_id": "sentence-transformers--all-MiniLM-L6-v2",
            "provider_resource_id": None,
            "display_name": "all-MiniLM-L6-v2",
            "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
            "source_id": "sentence-transformers/all-MiniLM-L6-v2",
            "metadata": {
                "provider_model_id": None,
                "local_path": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
                "source_id": "sentence-transformers/all-MiniLM-L6-v2",
            },
        }
    ]
    embeddings["default_resource_id"] = "sentence-transformers--all-MiniLM-L6-v2"
    embeddings["default_resource"] = dict(embeddings["resources"][0])

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del headers, timeout_seconds
        seen_requests.append((url, dict(payload) if isinstance(payload, dict) else None))
        if url.endswith("/v1/models"):
            return {
                "data": [
                    {
                        "id": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
                    }
                ]
            }, 200
        assert url.endswith("/v1/embeddings")
        return {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_embeddings_runtime_client(runtime)

    payload = client.embed_texts(texts=["hello"])

    assert payload["requested_model"] == "sentence-transformers--all-MiniLM-L6-v2"
    assert seen_requests == [
        ("http://llm:8000/v1/models", None),
        (
            "http://llm:8000/v1/embeddings",
            {"model": "/models/llm/sentence-transformers--all-MiniLM-L6-v2", "input": ["hello"]},
        ),
    ]


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


def test_image_analysis_runtime_client_sends_bound_task_defaults(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del method, headers
        assert url == "http://image_analysis:8090/v1/analyze"
        assert timeout_seconds == 30.0
        seen_payloads.append(dict(payload or {}))
        return {"image": {"width": 1, "height": 1}, "license_plates": []}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_image_analysis_runtime_client(_platform_runtime(include_image_analysis_runtime=True))

    payload = client.analyze(
        payload={
            "image": {"data_base64": "abc", "mime_type": "image/png"},
            "tasks": ["license_plate_recognition"],
        }
    )

    assert payload["status_code"] == 200
    assert seen_payloads[0]["runtime"] == {
        "resources": [
            {"id": "plate-detector", "metadata": {"task_key": "image_plate_detection"}},
            {"id": "plate-ocr", "metadata": {"task_key": "image_plate_ocr"}},
            {"id": "object-detector", "metadata": {"task_key": "object_detection"}},
            {"id": "captioner", "metadata": {"task_key": "image_captioning"}},
        ],
        "task_defaults": {
            "plate_detector": "plate-detector",
            "plate_ocr": "plate-ocr",
            "object_detector": "object-detector",
            "captioner": "captioner",
        },
    }


def test_image_analysis_runtime_client_requires_binding() -> None:
    with pytest.raises(runtime_client.ImageAnalysisRuntimeClientError) as exc_info:
        runtime_client.build_image_analysis_runtime_client(_platform_runtime())

    assert exc_info.value.code == "missing_image_analysis_runtime"


def test_image_analysis_runtime_client_requires_task_defaults() -> None:
    runtime = _platform_runtime(include_image_analysis_runtime=True)
    image_binding = runtime["capabilities"]["image_analysis"]
    assert isinstance(image_binding, dict)
    image_binding["resource_policy"] = {"selection_mode": "task_defaults", "task_defaults": {}}

    client = runtime_client.build_image_analysis_runtime_client(runtime)

    with pytest.raises(runtime_client.ImageAnalysisRuntimeClientError) as exc_info:
        client.analyze(
            payload={
                "image": {"data_base64": "abc", "mime_type": "image/png"},
                "tasks": ["object_detection"],
            }
        )

    assert exc_info.value.code == "missing_image_analysis_task_defaults"
    assert exc_info.value.details == {
        "missing_task_defaults": ["object_detector"],
        "tasks": ["object_detection"],
    }


def test_image_analysis_runtime_client_allows_caption_only_task_defaults(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del method, headers, timeout_seconds
        assert url == "http://image_analysis:8090/v1/analyze"
        seen_payloads.append(dict(payload or {}))
        return {"image": {"width": 1, "height": 1}, "caption": {"text": "A tiny image."}}, 200

    runtime = _platform_runtime(include_image_analysis_runtime=True)
    image_binding = runtime["capabilities"]["image_analysis"]
    assert isinstance(image_binding, dict)
    image_binding["resources"] = [
        {"id": "captioner", "metadata": {"task_key": "image_captioning"}},
    ]
    image_binding["resource_policy"] = {
        "selection_mode": "task_defaults",
        "task_defaults": {"captioner": "captioner"},
    }

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_image_analysis_runtime_client(runtime)

    payload = client.analyze(
        payload={
            "image": {"data_base64": "abc", "mime_type": "image/png"},
            "tasks": ["captioning"],
        }
    )

    assert payload["status_code"] == 200
    assert seen_payloads[0]["runtime"] == {
        "resources": [{"id": "captioner", "metadata": {"task_key": "image_captioning"}}],
        "task_defaults": {"captioner": "captioner"},
    }


def test_image_generation_runtime_client_sends_bound_task_defaults(monkeypatch: pytest.MonkeyPatch):
    seen_payloads: list[dict[str, object]] = []

    def _request(url: str, *, method: str, payload=None, headers=None, timeout_seconds=5.0):
        del method, headers
        assert url == "http://image_generation:8094/v1/generate"
        assert timeout_seconds == 45.0
        seen_payloads.append(dict(payload or {}))
        return {"image": {"width": 1, "height": 1, "mime_type": "image/png", "data_base64": "abc"}}, 200

    monkeypatch.setattr(runtime_client, "http_json_request", _request)
    client = runtime_client.build_image_generation_runtime_client(_platform_runtime(include_image_generation_runtime=True))

    payload = client.generate(
        payload={
            "prompt": "a test image",
            "tasks": ["text_to_image"],
        }
    )

    assert payload["status_code"] == 200
    assert seen_payloads[0]["runtime"] == {
        "resources": [
            {"id": "generator", "metadata": {"task_key": "image_text_to_image"}},
            {"id": "plate-logo-processor", "metadata": {"task_key": "image_plate_logo_replacement"}},
        ],
        "task_defaults": {
            "generator": "generator",
            "plate_logo_processor": "plate-logo-processor",
        },
    }


def test_image_generation_runtime_client_requires_binding() -> None:
    with pytest.raises(runtime_client.ImageGenerationRuntimeClientError) as exc_info:
        runtime_client.build_image_generation_runtime_client(_platform_runtime())

    assert exc_info.value.code == "missing_image_generation_runtime"


def test_image_generation_runtime_client_requires_task_defaults() -> None:
    runtime = _platform_runtime(include_image_generation_runtime=True)
    image_binding = runtime["capabilities"]["image_generation"]
    assert isinstance(image_binding, dict)
    image_binding["resource_policy"] = {"selection_mode": "task_defaults", "task_defaults": {}}

    client = runtime_client.build_image_generation_runtime_client(runtime)

    with pytest.raises(runtime_client.ImageGenerationRuntimeClientError) as exc_info:
        client.generate(
            payload={
                "prompt": "a test image",
                "tasks": ["text_to_image"],
            }
        )

    assert exc_info.value.code == "missing_image_generation_task_defaults"
    assert exc_info.value.details == {
        "missing_task_defaults": ["generator"],
        "tasks": ["text_to_image"],
    }
