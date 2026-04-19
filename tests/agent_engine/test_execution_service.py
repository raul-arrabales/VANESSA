from __future__ import annotations

import sys
from typing import Any
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from agent_engine.app.execution_pipeline import runner as execution_service
from agent_engine.app.retrieval import runtime as retrieval_runtime
from agent_engine.app.tool_runtime import dispatch as tool_dispatch
from agent_engine.app.services.policy_runtime_gate import ExecutionBlockedError
from contract_fixtures import load_contract_fixture


def test_execution_state_machine_success(monkeypatch: pytest.MonkeyPatch):
    saved_statuses: list[str] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v2", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(
        execution_service,
        "require_agent_execute_permission",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v2", "model.alpha"),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: {
                    "output_text": "model output",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )

    def _save(execution, **_kwargs):
        saved_statuses.append(execution.status)

    monkeypatch.setattr(execution_service.executions_repo, "save_execution", _save)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {"prompt": "hello"},
            "platform_runtime": {
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )
    assert status == 201
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["agent_version"] == "v2"
    assert payload["execution"]["model_ref"] == "model.alpha"
    assert payload["execution"]["result"] == {
        "output_text": "model output",
        "tool_calls": [],
        "embedding_calls": [],
        "retrieval_calls": [],
        "model_calls": [
            {
                "provider_slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "deployment_profile_slug": "local-default",
                "requested_model": "model.alpha",
                "status_code": 200,
            }
        ],
    }
    assert saved_statuses == ["queued", "running", "succeeded"]


def test_execution_runtime_block_is_persisted(monkeypatch: pytest.MonkeyPatch):
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)

    def _blocked(**_kwargs):
        raise ExecutionBlockedError(
            code="EXEC_RUNTIME_PROFILE_BLOCKED",
            message="blocked",
            status_code=403,
        )

    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", _blocked)
    monkeypatch.setattr(
        execution_service.executions_repo,
        "save_execution",
        lambda execution, **_kwargs: captured.append(execution.to_payload()),
    )

    with pytest.raises(ExecutionBlockedError) as exc:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {},
            }
        )
    assert exc.value.code == "EXEC_RUNTIME_PROFILE_BLOCKED"
    assert captured[-1]["status"] == "blocked"


def test_blocked_execution_contract_shape(monkeypatch: pytest.MonkeyPatch):
    golden = load_contract_fixture("agent_execution", "blocked_execution.json")["execution"]

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: golden["runtime_profile"])
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: (_ for _ in ()).throw(
            ExecutionBlockedError(
                code=golden["error"]["code"],
                message=golden["error"]["message"],
                status_code=403,
            )
        ),
    )

    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        execution_service.executions_repo,
        "save_execution",
        lambda execution, **_kwargs: captured.append(execution.to_payload()),
    )

    with pytest.raises(ExecutionBlockedError):
        execution_service.create_execution(
            {
                "agent_id": golden["agent_ref"],
                "requested_by_user_id": 123,
                "runtime_profile": golden["runtime_profile"],
                "input": {},
            }
        )

    assert set(captured[-1].keys()) == set(golden.keys())
    assert captured[-1]["status"] == "blocked"


def test_execution_without_prompt_or_messages_keeps_deterministic_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v1", None),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {},
        }
    )

    assert status == 201
    assert payload["execution"]["result"] == {
        "output_text": "Agent 'agent.alpha' executed in offline profile",
        "tool_calls": [],
        "embedding_calls": [],
        "model_calls": [],
        "retrieval_calls": [],
    }


def test_execution_uses_input_model_override_for_runtime_request(monkeypatch: pytest.MonkeyPatch):
    seen_models: list[str | None] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v1", None),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: seen_models.append(kwargs["requested_model"]) or {
                    "output_text": "override output",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {"prompt": "hello", "model": "safe-small"},
            "platform_runtime": {
                "deployment_profile": {"id": "dep-1", "slug": "local-default", "display_name": "Local Default"},
                "capabilities": {"llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"}},
            },
        }
    )

    assert status == 201
    assert seen_models == ["safe-small"]
    assert payload["execution"]["model_ref"] == "safe-small"


def test_execution_runtime_client_failures_map_to_existing_error_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(
        execution_service,
        "validate_runtime_and_dependencies",
        lambda **_kwargs: ("v1", "model.alpha"),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FailingClient",
            (),
            {
                "chat_completion": lambda self, **_kwargs: (_ for _ in ()).throw(
                    execution_service.LlmRuntimeClientError(
                        code="runtime_unreachable",
                        message="upstream unavailable",
                        status_code=502,
                    )
                )
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    with pytest.raises(ExecutionBlockedError) as exc_info:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {"prompt": "hello"},
                "platform_runtime": {
                    "deployment_profile": {"slug": "local-default"},
                    "capabilities": {
                        "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                        "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    },
                },
            }
        )

    assert exc_info.value.code == "EXEC_UPSTREAM_UNAVAILABLE"


def test_execution_with_retrieval_from_prompt_queries_vector_then_calls_llm(monkeypatch: pytest.MonkeyPatch):
    seen_llm_messages: list[list[dict[str, Any]]] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-vllm-embeddings-default",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeVectorClient",
            (),
            {
                "query": lambda self, **kwargs: {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [
                        {
                            "id": "doc-1",
                            "text": "retrieved text",
                            "metadata": {"tenant": "ops"},
                            "score": 0.75,
                            "score_kind": "similarity",
                        }
                    ],
                }
            },
        )(),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeLlmClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: seen_llm_messages.append(kwargs["messages"]) or {
                    "output_text": "rag answer",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {
                "prompt": "hello",
                "retrieval": {
                    "index": "knowledge_base",
                    "query": "hello",
                    "top_k": 3,
                    "filters": {"tenant": "ops"},
                    "search_method": "semantic",
                    "query_preprocessing": "none",
                },
            },
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )

    assert status == 201
    assert payload["execution"]["result"] == {
        "output_text": "rag answer",
        "tool_calls": [],
        "embedding_calls": [
            {
                "provider_slug": "vllm-embeddings-local",
                "provider_key": "vllm_embeddings_local",
                "deployment_profile_slug": "local-default",
                "requested_model": "local-vllm-embeddings-default",
                "input_count": 1,
                "dimension": 2,
                "status_code": 200,
            }
        ],
        "model_calls": [
            {
                "provider_slug": "vllm-local-gateway",
                "provider_key": "vllm_local",
                "deployment_profile_slug": "local-default",
                "requested_model": "model.alpha",
                "status_code": 200,
            }
        ],
        "retrieval_calls": [
            {
                "provider_slug": "weaviate-local",
                "provider_key": "weaviate_local",
                "deployment_profile_slug": "local-default",
                "index": "knowledge_base",
                "query": "hello",
                "top_k": 3,
                "search_method": "semantic",
                "query_preprocessing": "none",
                "result_count": 1,
                "results": [
                    {
                        "id": "doc-1",
                        "text": "retrieved text",
                        "metadata": {"tenant": "ops"},
                        "score": 0.75,
                        "score_kind": "similarity",
                        "relevance_score": 0.75,
                        "relevance_kind": "similarity",
                    }
                ],
            }
        ],
    }
    assert seen_llm_messages[0][0]["role"] == "system"
    assert "retrieved text" in seen_llm_messages[0][0]["content"][0]["text"]
    assert "Reference [1]" in seen_llm_messages[0][0]["content"][0]["text"]
    assert "bracketed numeric citations such as [1] or [1, 2]" in seen_llm_messages[0][0]["content"][0]["text"]


def test_execution_with_qdrant_runtime_records_qdrant_retrieval_call(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-vllm-embeddings-default",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeQdrantClient",
            (),
            {
                "query": lambda self, **kwargs: {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [
                        {
                            "id": "doc-1",
                            "text": "qdrant text",
                            "metadata": {"tenant": "ops"},
                            "score": 0.88,
                            "score_kind": "similarity",
                        }
                    ],
                }
            },
        )(),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeLlmClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: {
                    "output_text": "rag answer",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {"prompt": "hello", "retrieval": {"index": "knowledge_base"}},
            "platform_runtime": {
                "deployment_profile": {"id": "dep-2", "slug": "local-qdrant", "display_name": "Local Qdrant"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "qdrant-local", "provider_key": "qdrant_local"},
                },
            },
        }
    )

    assert status == 201
    assert payload["execution"]["result"]["embedding_calls"] == [
        {
            "provider_slug": "vllm-embeddings-local",
            "provider_key": "vllm_embeddings_local",
            "deployment_profile_slug": "local-qdrant",
            "requested_model": "local-vllm-embeddings-default",
            "input_count": 1,
            "dimension": 2,
            "status_code": 200,
        }
    ]
    assert payload["execution"]["result"]["retrieval_calls"] == [
        {
            "provider_slug": "qdrant-local",
            "provider_key": "qdrant_local",
            "deployment_profile_slug": "local-qdrant",
            "index": "knowledge_base",
            "query": "hello",
            "top_k": 5,
            "search_method": "semantic",
            "query_preprocessing": "none",
            "result_count": 1,
            "results": [
                {
                    "id": "doc-1",
                    "text": "qdrant text",
                    "metadata": {"tenant": "ops"},
                    "score": 0.88,
                    "score_kind": "similarity",
                    "relevance_score": 0.88,
                    "relevance_kind": "similarity",
                }
            ],
        }
    ]


def test_execution_with_unsupported_embeddings_model_returns_actionable_503(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: (_ for _ in ()).throw(
                    execution_service.EmbeddingsRuntimeClientError(
                        code="embeddings_runtime_request_failed",
                        message="Embeddings runtime request failed",
                        status_code=400,
                        details={
                            "provider_slug": "vllm-embeddings-local",
                            "status_code": 400,
                            "upstream": {
                                "detail": {
                                    "code": "local_vllm_bad_request",
                                    "message": "The model does not support Embeddings API",
                                }
                            },
                        },
                    )
                )
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    with pytest.raises(execution_service.ExecutionBlockedError) as exc_info:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {"prompt": "hello", "retrieval": {"index": "knowledge_base"}},
                "platform_runtime": {
                    "deployment_profile": {"slug": "local-default"},
                    "capabilities": {
                        "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                        "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                        "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                    },
                },
            }
        )

    assert exc_info.value.code == "EXEC_UPSTREAM_UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert "configured embeddings model does not support embeddings" in exc_info.value.message


def test_execution_with_retrieval_derives_query_from_last_user_message(monkeypatch: pytest.MonkeyPatch):
    seen_queries: list[str] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-vllm-embeddings-default",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeVectorClient",
            (),
            {
                "query": lambda self, **kwargs: seen_queries.append(kwargs["query_text"]) or {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [],
                }
            },
        )(),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeLlmClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: {
                    "output_text": "ok",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "first"},
                    {"role": "assistant", "content": "reply"},
                    {"role": "user", "content": "last user question"},
                ],
                "retrieval": {"index": "knowledge_base"},
            },
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )

    assert status == 201
    assert seen_queries == ["last user question"]
    assert payload["execution"]["result"]["retrieval_calls"][0]["query"] == "last user question"


def test_execution_with_explicit_retrieval_query_overrides_prompt(monkeypatch: pytest.MonkeyPatch):
    seen_queries: list[str] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-vllm-embeddings-default",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeVectorClient",
            (),
            {
                "query": lambda self, **kwargs: seen_queries.append(kwargs["query_text"]) or {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [],
                }
            },
        )(),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeLlmClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: {
                    "output_text": "ok",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {
                "prompt": "hello",
                "retrieval": {"index": "knowledge_base", "query": "explicit retrieval query"},
            },
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )

    assert status == 201
    assert seen_queries == ["explicit retrieval query"]
    assert payload["execution"]["result"]["retrieval_calls"][0]["query"] == "explicit retrieval query"


def test_execution_with_zero_hit_retrieval_keeps_original_messages(monkeypatch: pytest.MonkeyPatch):
    seen_llm_messages: list[list[dict[str, Any]]] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": []}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        retrieval_runtime,
        "build_embeddings_runtime_client",
        lambda _runtime: type(
            "FakeEmbeddingsClient",
            (),
            {
                "embed_texts": lambda self, **kwargs: {
                    "embeddings": [[0.1, 0.2]],
                    "dimension": 2,
                    "status_code": 200,
                    "requested_model": "local-vllm-embeddings-default",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        retrieval_runtime,
        "build_vector_store_runtime_client",
        lambda _runtime: type(
            "FakeVectorClient",
            (),
            {
                "query": lambda self, **kwargs: {
                    "index": kwargs["index_name"],
                    "query": kwargs["query_text"],
                    "top_k": kwargs["top_k"],
                    "results": [],
                }
            },
        )(),
    )
    monkeypatch.setattr(
        execution_service,
        "build_llm_runtime_client",
        lambda _runtime: type(
            "FakeLlmClient",
            (),
            {
                "chat_completion": lambda self, **kwargs: seen_llm_messages.append(kwargs["messages"]) or {
                    "output_text": "ok",
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            },
        )(),
    )
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {
                "prompt": "hello",
                "retrieval": {"index": "knowledge_base"},
            },
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "embeddings": {"slug": "vllm-embeddings-local", "provider_key": "vllm_embeddings_local"},
                    "vector_store": {"slug": "weaviate-local", "provider_key": "weaviate_local"},
                },
            },
        }
    )

    assert status == 201
    assert seen_llm_messages == [[{"role": "user", "content": [{"type": "text", "text": "hello"}]}]]
    assert payload["execution"]["result"]["retrieval_calls"][0]["result_count"] == 0


def test_execution_rejects_invalid_retrieval_payload_before_persisting(monkeypatch: pytest.MonkeyPatch):
    saved_statuses: list[str] = []

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda execution, **_kwargs: saved_statuses.append(execution.status))

    with pytest.raises(ValueError) as exc_info:
        execution_service.create_execution(
            {
                "agent_id": "agent.alpha",
                "requested_by_user_id": 123,
                "runtime_profile": "offline",
                "input": {"prompt": "hello", "retrieval": {"index": "knowledge_base", "top_k": 0}},
            }
        )

    assert str(exc_info.value) == "invalid_retrieval_input"
    assert saved_statuses == []


def test_execution_runs_mcp_tool_calls_before_final_model_response(monkeypatch: pytest.MonkeyPatch):
    llm_seen_messages: list[list[dict[str, Any]]] = []
    llm_seen_tools: list[list[dict[str, Any]] | None] = []
    llm_round = {"count": 0}

    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "online")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": ["tool.web_search"]}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_tools",
        lambda **_kwargs: [
            {
                "entity_id": "tool.web_search",
                "current_version": "v1",
                "current_spec": {
                    "name": "Web Search",
                    "description": "Search the web",
                    "transport": "mcp",
                    "connection_profile_ref": "default",
                    "tool_name": "web_search",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "safety_policy": {"timeout_seconds": 8},
                    "offline_compatible": False,
                },
            }
        ],
    )

    class FakeLlmClient:
        def chat_completion(self, **kwargs):
            llm_seen_messages.append(kwargs["messages"])
            llm_seen_tools.append(kwargs.get("tools"))
            llm_round["count"] += 1
            if llm_round["count"] == 1:
                return {
                    "output_text": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "web_search", "arguments": "{\"query\":\"hello\"}"},
                        }
                    ],
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            return {
                "output_text": "search answer",
                "tool_calls": [],
                "status_code": 200,
                "requested_model": kwargs["requested_model"],
            }

    class FakeMcpClient:
        def invoke(self, **kwargs):
            assert kwargs["tool_name"] == "web_search"
            return {
                "status_code": 200,
                "result": {"query": "hello", "results": [{"title": "Result", "url": "https://search.local"}]},
                "error": None,
            }

    monkeypatch.setattr(execution_service, "build_llm_runtime_client", lambda _runtime: FakeLlmClient())
    monkeypatch.setattr(tool_dispatch, "build_mcp_tool_runtime_client", lambda _runtime: FakeMcpClient())
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "online",
            "input": {"prompt": "hello"},
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "mcp_runtime": {"slug": "mcp-gateway-local", "provider_key": "mcp_gateway_local"},
                },
            },
        }
    )

    assert status == 201
    assert payload["execution"]["result"]["output_text"] == "search answer"
    assert payload["execution"]["result"]["tool_calls"][0]["tool_ref"] == "tool.web_search"
    assert payload["execution"]["result"]["model_calls"][0]["requested_model"] == "model.alpha"
    assert len(payload["execution"]["result"]["model_calls"]) == 2
    assert llm_seen_tools[0][0]["function"]["name"] == "web_search"
    assert llm_seen_messages[1][-1]["role"] == "tool"


def test_execution_runs_sandbox_tool_calls_in_offline_profile(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(execution_service, "resolve_runtime_profile", lambda _p: "offline")
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_spec",
        lambda *, agent_id: {"entity_id": agent_id, "current_version": "v1", "current_spec": {"tool_refs": ["tool.python_exec"]}},
    )
    monkeypatch.setattr(execution_service, "require_agent_execute_permission", lambda **_kwargs: None)
    monkeypatch.setattr(execution_service, "validate_runtime_and_dependencies", lambda **_kwargs: ("v1", "model.alpha"))
    monkeypatch.setattr(
        execution_service,
        "resolve_agent_tools",
        lambda **_kwargs: [
            {
                "entity_id": "tool.python_exec",
                "current_version": "v1",
                "current_spec": {
                    "name": "Python Execution",
                    "description": "Run Python",
                    "transport": "sandbox_http",
                    "connection_profile_ref": "default",
                    "tool_name": "python_exec",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "safety_policy": {"timeout_seconds": 5, "network_access": False},
                    "offline_compatible": True,
                },
            }
        ],
    )

    class FakeLlmClient:
        def __init__(self):
            self.calls = 0

        def chat_completion(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {
                    "output_text": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "python_exec", "arguments": "{\"code\":\"result = 2 + 2\"}"},
                        }
                    ],
                    "status_code": 200,
                    "requested_model": kwargs["requested_model"],
                }
            return {
                "output_text": "4",
                "tool_calls": [],
                "status_code": 200,
                "requested_model": kwargs["requested_model"],
            }

    class FakeSandboxClient:
        def execute_python(self, **kwargs):
            assert kwargs["code"] == "result = 2 + 2"
            return {"status_code": 200, "stdout": "", "stderr": "", "result": 4, "error": None}

    monkeypatch.setattr(execution_service, "build_llm_runtime_client", lambda _runtime: FakeLlmClient())
    monkeypatch.setattr(tool_dispatch, "build_sandbox_tool_runtime_client", lambda _runtime: FakeSandboxClient())
    monkeypatch.setattr(execution_service.executions_repo, "save_execution", lambda *_args, **_kwargs: None)

    payload, status = execution_service.create_execution(
        {
            "agent_id": "agent.alpha",
            "requested_by_user_id": 123,
            "runtime_profile": "offline",
            "input": {"prompt": "solve this"},
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "llm_inference": {"slug": "vllm-local-gateway", "provider_key": "vllm_local"},
                    "sandbox_execution": {"slug": "sandbox-local", "provider_key": "sandbox_local"},
                },
            },
        }
    )

    assert status == 201
    assert payload["execution"]["result"]["output_text"] == "4"
    assert payload["execution"]["result"]["tool_calls"][0]["transport"] == "sandbox_http"
