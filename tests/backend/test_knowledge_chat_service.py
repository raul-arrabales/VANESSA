from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import g

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.app import app  # noqa: E402
from app.application.playground_execution import add_missing_reference_citation  # noqa: E402
from app.config import AuthConfig  # noqa: E402
from app.repositories import context_management as context_repo  # noqa: E402
from app.services import knowledge_chat_bootstrap, knowledge_chat_service  # noqa: E402


def test_add_missing_reference_citation_only_when_needed():
    references = [
        {"id": "ref-1", "citation_label": "[1]"},
        {"id": "ref-2", "citation_label": "[2]"},
        {"id": "ref-3", "citation_label": "[3]"},
        {"id": "ref-4", "citation_label": "[4]"},
    ]

    assert add_missing_reference_citation("Answer without citations.", references) == "Answer without citations. [1, 2, 3]"
    assert add_missing_reference_citation("Answer already cites [2].", references) == "Answer already cites [2]."
    assert add_missing_reference_citation("Answer without sources.", []) == "Answer without sources."


def _config(**overrides) -> AuthConfig:
    payload = {
        "database_url": "postgresql://ignored",
        "jwt_secret": "test-secret",
        "model_credentials_encryption_key": "test-secret",
        "jwt_algorithm": "HS256",
        "access_token_ttl_seconds": 28_800,
        "allow_self_register": True,
        "bootstrap_superadmin_email": "",
        "bootstrap_superadmin_username": "",
        "bootstrap_superadmin_password": "",
        "flask_env": "development",
    }
    payload.update(overrides)
    return AuthConfig(**payload)


def test_run_knowledge_chat_resolves_model_and_maps_sources(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [{"id": "kb-primary", "lifecycle_state": "active", "sync_status": "ready"}],
    )
    monkeypatch.setattr(
        knowledge_chat_service,
        "resolve_model_for_inference",
        lambda _db, *, user_id, requested_model_id, **_kwargs: {"id": f"{requested_model_id}-resolved"},
    )
    monkeypatch.setattr(knowledge_chat_service, "ensure_knowledge_chat_agent", lambda _db: True)
    monkeypatch.setattr(
        knowledge_chat_service,
        "get_active_platform_runtime",
        lambda _db, _config: {
            "deployment_profile": {"slug": "local-default"},
            "capabilities": {
                "vector_store": {
                    "resources": [
                        {
                            "id": "kb-primary",
                            "ref_type": "knowledge_base",
                            "knowledge_base_id": "kb-primary",
                            "provider_resource_id": "kb_product_docs",
                            "display_name": "Product Docs",
                            "metadata": {"slug": "product-docs", "index_name": "kb_product_docs"},
                        }
                    ],
                    "default_resource_id": "kb-primary",
                    "resource_policy": {"selection_mode": "explicit"},
                }
            },
        },
    )
    monkeypatch.setattr(knowledge_chat_service, "resolve_runtime_profile", lambda _db: "offline")

    seen_calls: list[dict[str, object]] = []

    def _create_execution(**kwargs):
        seen_calls.append(kwargs)
        return (
            {
                "execution": {
                    "id": "exec-knowledge",
                    "status": "succeeded",
                    "result": {
                        "output_text": "retrieval answer",
                        "retrieval_calls": [
                            {
                                "index": "knowledge_base",
                                "top_k": 5,
                                "search_method": "semantic",
                                "query_preprocessing": "none",
                                "result_count": 1,
                                "results": [
                                    {
                                        "id": "doc-1",
                                        "text": "A long explanation about retrieval in VANESSA.",
                                        "metadata": {
                                            "title": "Architecture Overview",
                                            "uri": "https://example.com/architecture",
                                            "source_type": "doc",
                                        },
                                        "score": 0.92,
                                        "score_kind": "similarity",
                                        "relevance_score": 0.92,
                                        "relevance_kind": "similarity",
                                    }
                                ],
                            }
                        ],
                    },
                }
            },
            201,
        )

    with app.test_request_context("/v1/chat/knowledge"):
        g.current_user = {"id": 7, "role": "user"}
        payload, status_code = knowledge_chat_service.run_knowledge_chat(
            database_url="ignored",
            config=_config(),
            request_id="req-1",
            prompt="How does retrieval work?",
            requested_model_id="safe-small",
            requested_knowledge_base_id=None,
            history_payload=[{"role": "assistant", "content": "Previous answer"}],
            create_execution_fn=_create_execution,
        )

    assert status_code == 200
    assert payload["output"] == "retrieval answer [1]"
    assert payload["knowledge_base_id"] == "kb-primary"
    assert payload["retrieval"] == {
        "index": "knowledge_base",
        "result_count": 1,
        "search_method": "semantic",
        "query_preprocessing": "none",
        "top_k": 5,
    }
    assert payload["sources"] == [
        {
            "id": "doc-1",
            "title": "Architecture Overview",
            "snippet": "A long explanation about retrieval in VANESSA.",
            "uri": "https://example.com/architecture",
            "source_type": "doc",
            "metadata": {
                "title": "Architecture Overview",
                "uri": "https://example.com/architecture",
                "source_type": "doc",
            },
            "score": 0.92,
            "score_kind": "similarity",
            "relevance_score": 0.92,
            "relevance_kind": "similarity",
            "reference_id": "ref-1",
            "citation_label": "[1]",
        }
    ]
    assert payload["references"] == [
        {
            "id": "ref-1",
            "citation_label": "[1]",
            "title": "Architecture Overview",
            "description": "doc",
            "uri": "https://example.com/architecture",
            "file_reference": "https://example.com/architecture",
            "pages": [],
            "source_ids": ["doc-1"],
        }
    ]
    assert seen_calls == [
        {
            "base_url": "http://agent_engine:7000",
            "service_token": "dev-agent-engine-token",
            "request_id": "req-1",
            "agent_id": "agent.knowledge_chat",
            "execution_input": {
                "prompt": "How does retrieval work?",
                "model": "safe-small-resolved",
                "messages": [
                    {"role": "assistant", "content": [{"type": "text", "text": "Previous answer"}]},
                    {"role": "user", "content": [{"type": "text", "text": "How does retrieval work?"}]},
                ],
                "retrieval": {
                    "index": "kb_product_docs",
                    "query": "How does retrieval work?",
                    "top_k": 5,
                    "filters": {},
                    "search_method": "semantic",
                    "query_preprocessing": "none",
                },
            },
            "requested_by_user_id": 7,
            "requested_by_role": "user",
            "runtime_profile": "offline",
            "timeout_seconds": 70.0,
            "platform_runtime": {
                "deployment_profile": {"slug": "local-default"},
                "capabilities": {
                    "vector_store": {
                        "resources": [
                            {
                                "id": "kb-primary",
                                "ref_type": "knowledge_base",
                                "knowledge_base_id": "kb-primary",
                                "provider_resource_id": "kb_product_docs",
                                "display_name": "Product Docs",
                                "metadata": {"slug": "product-docs", "index_name": "kb_product_docs"},
                            }
                        ],
                        "default_resource_id": "kb-primary",
                        "resource_policy": {"selection_mode": "explicit"},
                    }
                },
            },
        }
    ]


def test_run_knowledge_chat_keeps_empty_sources_when_retrieval_returns_no_hits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [{"id": "kb-primary", "lifecycle_state": "active", "sync_status": "ready"}],
    )
    monkeypatch.setattr(
        knowledge_chat_service,
        "resolve_model_for_inference",
        lambda _db, *, user_id, requested_model_id, **_kwargs: {"id": requested_model_id},
    )
    monkeypatch.setattr(knowledge_chat_service, "ensure_knowledge_chat_agent", lambda _db: True)
    monkeypatch.setattr(
        knowledge_chat_service,
        "get_active_platform_runtime",
        lambda _db, _config: {
            "deployment_profile": {"slug": "local-default"},
            "capabilities": {
                "vector_store": {
                    "resources": [
                        {
                            "id": "kb-primary",
                            "ref_type": "knowledge_base",
                            "knowledge_base_id": "kb-primary",
                            "provider_resource_id": "kb_product_docs",
                            "display_name": "Product Docs",
                            "metadata": {"slug": "product-docs", "index_name": "kb_product_docs"},
                        }
                    ],
                    "default_resource_id": "kb-primary",
                    "resource_policy": {"selection_mode": "explicit"},
                }
            },
        },
    )
    monkeypatch.setattr(knowledge_chat_service, "resolve_runtime_profile", lambda _db: "offline")

    with app.test_request_context("/v1/chat/knowledge"):
        g.current_user = {"id": 7, "role": "user"}
        payload, status_code = knowledge_chat_service.run_knowledge_chat(
            database_url="ignored",
            config=_config(),
            request_id="req-2",
            prompt="hello",
            requested_model_id="safe-small",
            requested_knowledge_base_id=None,
            history_payload=[],
            create_execution_fn=lambda **_kwargs: (
                {
                    "execution": {
                        "id": "exec-knowledge",
                        "status": "succeeded",
                        "result": {
                            "output_text": "answer",
                            "retrieval_calls": [
                                {
                                    "index": "knowledge_base",
                                    "top_k": 5,
                                    "search_method": "semantic",
                                    "query_preprocessing": "none",
                                    "result_count": 0,
                                    "results": [],
                                }
                            ],
                        },
                    }
                },
                201,
            ),
        )

    assert status_code == 200
    assert payload["sources"] == []
    assert payload["references"] == []
    assert payload["retrieval"] == {
        "index": "knowledge_base",
        "result_count": 0,
        "search_method": "semantic",
        "query_preprocessing": "none",
        "top_k": 5,
    }


def test_list_knowledge_chat_knowledge_bases_reports_selection_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        context_repo,
        "get_knowledge_bases",
        lambda _db, _ids: [{"id": "kb-primary", "lifecycle_state": "active", "sync_status": "ready"}],
    )
    payload, status_code = knowledge_chat_service.list_knowledge_chat_knowledge_bases(
        database_url="ignored",
        config=_config(),
        get_active_platform_runtime_fn=lambda _db, _config: {
            "deployment_profile": {"slug": "local-default"},
            "capabilities": {
                "vector_store": {
                    "resources": [
                        {
                            "id": "kb-primary",
                            "ref_type": "knowledge_base",
                            "knowledge_base_id": "kb-primary",
                            "provider_resource_id": "kb_product_docs",
                            "display_name": "Product Docs",
                            "metadata": {"slug": "product-docs", "index_name": "kb_product_docs"},
                        }
                    ],
                    "default_resource_id": "kb-primary",
                    "resource_policy": {"selection_mode": "explicit"},
                }
            },
        },
    )

    assert status_code == 200
    assert payload["default_knowledge_base_id"] == "kb-primary"
    assert payload["selection_required"] is False
    assert payload["knowledge_bases"] == [
        {
            "id": "kb-primary",
            "display_name": "Product Docs",
            "slug": "product-docs",
            "index_name": "kb_product_docs",
            "is_default": True,
            "is_eligible": True,
            "lifecycle_state": "active",
            "sync_status": "ready",
        }
    ]


def test_ensure_knowledge_chat_agent_seeds_entity_and_share(monkeypatch: pytest.MonkeyPatch):
    created_entities: list[dict[str, object]] = []
    created_versions: list[dict[str, object]] = []
    created_shares: list[dict[str, object]] = []

    monkeypatch.setattr(knowledge_chat_bootstrap, "find_registry_entity", lambda _db, *, entity_type, entity_id: None)
    monkeypatch.setattr(
        knowledge_chat_bootstrap,
        "list_users",
        lambda _db, *, is_active=None: [{"id": 3, "role": "superadmin"}] if is_active is not False else [],
    )
    monkeypatch.setattr(
        knowledge_chat_bootstrap,
        "create_registry_entity",
        lambda _db, **kwargs: created_entities.append(kwargs) or {"entity_id": kwargs["entity_id"], "owner_user_id": kwargs["owner_user_id"]},
    )
    monkeypatch.setattr(
        knowledge_chat_bootstrap,
        "create_registry_version",
        lambda _db, **kwargs: created_versions.append(kwargs) or {"entity_id": kwargs["entity_id"], "version": kwargs["version"]},
    )
    monkeypatch.setattr(
        knowledge_chat_bootstrap,
        "create_share_grant",
        lambda _db, **kwargs: created_shares.append(kwargs) or kwargs,
    )

    assert knowledge_chat_bootstrap.ensure_knowledge_chat_agent("ignored") is True
    assert created_entities[0]["entity_id"] == "agent.knowledge_chat"
    assert created_versions[0]["entity_id"] == "agent.knowledge_chat"
    assert created_shares[0]["permission"] == "execute"
    assert created_shares[0]["grantee_type"] == "public"
