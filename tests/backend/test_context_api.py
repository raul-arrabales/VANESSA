from __future__ import annotations

import io
import pytest

from app.api.http import context as context_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(context_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(context_routes, "_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_list_knowledge_bases_route_requires_admin(client):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="user@example.com",
        username="user",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    response = test_client.get("/v1/context/knowledge-bases", headers=_auth(token))

    assert response.status_code == 403


def test_list_schema_profiles_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-profiles@example.com",
        username="admin-profiles",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_schema_profiles",
        lambda *_args, **_kwargs: [
            {
                "id": "profile-1",
                "slug": "plain-document-rag",
                "display_name": "Plain document RAG",
                "description": "General-purpose retrieval schema.",
                "provider_key": "weaviate_local",
                "is_system": True,
                "schema": {"properties": [{"name": "title", "data_type": "text"}]},
            }
        ],
    )

    response = test_client.get("/v1/context/schema-profiles?provider_key=weaviate_local", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["schema_profiles"][0]["slug"] == "plain-document-rag"


def test_create_schema_profile_route_returns_payload_for_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-profile@example.com",
        username="superadmin-profile",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    def _create_schema_profile(_db, *, payload, created_by_user_id):
        captured["payload"] = payload
        captured["created_by_user_id"] = created_by_user_id
        return {
            "id": "profile-2",
            "slug": "customer-memory",
            "display_name": "Customer Memory",
            "description": "Custom reusable memory schema.",
            "provider_key": "weaviate_local",
            "is_system": False,
            "schema": {"properties": [{"name": "subject", "data_type": "text"}]},
        }

    monkeypatch.setattr(context_routes, "create_schema_profile", _create_schema_profile)

    response = test_client.post(
        "/v1/context/schema-profiles",
        headers=_auth(token),
        json={
            "slug": "customer-memory",
            "display_name": "Customer Memory",
            "description": "Custom reusable memory schema.",
            "provider_key": "weaviate_local",
            "schema": {"properties": [{"name": "subject", "data_type": "text"}]},
        },
    )

    assert response.status_code == 201
    assert captured["created_by_user_id"] == superadmin["id"]
    assert captured["payload"] == {
        "slug": "customer-memory",
        "display_name": "Customer Memory",
        "description": "Custom reusable memory schema.",
        "provider_key": "weaviate_local",
        "schema": {"properties": [{"name": "subject", "data_type": "text"}]},
    }
    assert response.get_json()["schema_profile"]["provider_key"] == "weaviate_local"


def test_list_vectorization_options_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-vectorization@example.com",
        username="admin-vectorization",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_vectorization_options",
        lambda *_args, **_kwargs: {
            "backing_provider": {
                "id": "provider-2",
                "display_name": "Weaviate local",
                "provider_key": "weaviate_local",
                "enabled": True,
                "capability": "vector_store",
            },
            "supports_named_vectors": True,
            "supported_modes": [
                {"mode": "vanessa_embeddings", "requires_embedding_target": True},
                {"mode": "self_provided", "requires_embedding_target": False},
            ],
            "embedding_providers": [
                {
                    "id": "embedding-provider-1",
                    "display_name": "Embeddings local",
                    "provider_key": "openai_compatible_cloud_embeddings",
                    "resources": [{"id": "text-embedding-3-small", "display_name": "text-embedding-3-small"}],
                    "default_resource_id": "text-embedding-3-small",
                }
            ],
        },
    )

    response = test_client.get(
        "/v1/context/vectorization-options?backing_provider_instance_id=provider-2",
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.get_json()["supported_modes"][0]["mode"] == "vanessa_embeddings"


def test_list_source_directories_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-source-dirs@example.com",
        username="admin-source-dirs",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_source_directories",
        lambda *_args, **_kwargs: {
            "roots": [{"id": "root-1", "display_name": "/context_sources"}],
            "selected_root_id": "root-1",
            "current_relative_path": "product_docs",
            "directories": [{"name": "guides", "relative_path": "product_docs/guides"}],
            "parent_relative_path": "",
        },
    )

    response = test_client.get(
        "/v1/context/source-directories?root_id=root-1&relative_path=product_docs",
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.get_json()["selected_root_id"] == "root-1"
    assert response.get_json()["directories"][0]["relative_path"] == "product_docs/guides"


def test_list_knowledge_bases_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_knowledge_bases",
        lambda *_args, **_kwargs: [
            {
                "id": "kb-primary",
                "slug": "product-docs",
                "display_name": "Product Docs",
                "description": "docs",
                "index_name": "kb_product_docs",
                "backing_provider_instance_id": "provider-2",
                "backing_provider_key": "weaviate_local",
                "backing_provider": {
                    "id": "provider-2",
                    "display_name": "Weaviate local",
                    "provider_key": "weaviate_local",
                    "enabled": True,
                "capability": "vector_store",
                },
                "lifecycle_state": "active",
                "sync_status": "ready",
                "schema": {},
                "vectorization": {
                    "mode": "vanessa_embeddings",
                    "embedding_provider_instance_id": "embedding-provider-1",
                    "embedding_resource_id": "text-embedding-3-small",
                    "embedding_provider": {
                        "id": "embedding-provider-1",
                        "display_name": "Embeddings local",
                        "provider_key": "openai_compatible_cloud_embeddings",
                    },
                    "embedding_resource": {
                        "id": "text-embedding-3-small",
                        "display_name": "text-embedding-3-small",
                    },
                    "supports_named_vectors": True,
                },
                "chunking": {
                    "strategy": "fixed_length",
                    "config": {
                        "unit": "tokens",
                        "chunk_length": 300,
                        "chunk_overlap": 60,
                    },
                },
                "document_count": 2,
                "binding_count": 1,
            }
        ],
    )

    response = test_client.get("/v1/context/knowledge-bases", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["knowledge_bases"][0]["id"] == "kb-primary"


def test_create_knowledge_base_route_returns_payload_for_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-create@example.com",
        username="superadmin-create",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    def _create_knowledge_base(_db, *, config, payload, created_by_user_id):
        captured["config"] = config
        captured["payload"] = payload
        captured["created_by_user_id"] = created_by_user_id
        return {
            "id": "kb-primary",
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "index_name": "kb_product_docs",
            "backing_provider_instance_id": "provider-2",
            "backing_provider_key": "weaviate_local",
            "backing_provider": {
                "id": "provider-2",
                "display_name": "Weaviate local",
                "provider_key": "weaviate_local",
                "enabled": True,
                "capability": "vector_store",
            },
            "lifecycle_state": "active",
            "sync_status": "ready",
            "schema": {},
            "vectorization": {
                "mode": "vanessa_embeddings",
                "embedding_provider_instance_id": "embedding-provider-1",
                "embedding_resource_id": "text-embedding-3-small",
                "embedding_provider": {
                    "id": "embedding-provider-1",
                    "display_name": "Embeddings local",
                    "provider_key": "openai_compatible_cloud_embeddings",
                },
                "embedding_resource": {
                    "id": "text-embedding-3-small",
                    "display_name": "text-embedding-3-small",
                },
                "supports_named_vectors": True,
            },
            "chunking": {
                "strategy": "fixed_length",
                "config": {
                    "unit": "tokens",
                    "chunk_length": 300,
                    "chunk_overlap": 60,
                },
            },
            "document_count": 0,
            "binding_count": 0,
        }

    monkeypatch.setattr(context_routes, "create_knowledge_base", _create_knowledge_base)

    response = test_client.post(
        "/v1/context/knowledge-bases",
        headers=_auth(token),
        json={
            "slug": "product-docs",
            "display_name": "Product Docs",
            "description": "docs",
            "backing_provider_instance_id": "provider-2",
            "vectorization": {
                "mode": "vanessa_embeddings",
                "embedding_provider_instance_id": "embedding-provider-1",
                "embedding_resource_id": "text-embedding-3-small",
            },
            "chunking": {
                "strategy": "fixed_length",
                "config": {
                    "unit": "tokens",
                    "chunk_length": 300,
                    "chunk_overlap": 60,
                },
            },
        },
    )

    assert response.status_code == 201
    assert captured["created_by_user_id"] == superadmin["id"]
    assert captured["payload"] == {
        "slug": "product-docs",
        "display_name": "Product Docs",
        "description": "docs",
        "backing_provider_instance_id": "provider-2",
        "vectorization": {
            "mode": "vanessa_embeddings",
            "embedding_provider_instance_id": "embedding-provider-1",
            "embedding_resource_id": "text-embedding-3-small",
        },
        "chunking": {
            "strategy": "fixed_length",
            "config": {
                "unit": "tokens",
                "chunk_length": 300,
                "chunk_overlap": 60,
            },
        },
    }
    assert response.get_json()["knowledge_base"]["backing_provider_instance_id"] == "provider-2"


def test_resync_knowledge_base_route_requires_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    response = test_client.post("/v1/context/knowledge-bases/kb-primary/resync", headers=_auth(token))

    assert response.status_code == 403


def test_resync_knowledge_base_route_enqueues_for_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-resync@example.com",
        username="superadmin-resync",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "resync_knowledge_base",
        lambda *_args, **_kwargs: {
            "knowledge_base": {"id": "kb-primary", "display_name": "Product Docs"},
            "sync_run": {"id": "run-1", "operation_type": "knowledge_resync", "status": "queued"},
        },
    )

    response = test_client.post("/v1/context/knowledge-bases/kb-primary/resync", headers=_auth(token))

    assert response.status_code == 202
    assert response.get_json()["sync_run"]["operation_type"] == "knowledge_resync"


def test_query_knowledge_base_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-query@example.com",
        username="admin-query",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        context_routes,
        "query_knowledge_base",
        lambda *_args, **_kwargs: captured.update(_kwargs) or {
            "knowledge_base_id": "kb-primary",
            "retrieval": {
                "index": "kb_product_docs",
                "result_count": 1,
                "top_k": 5,
                "search_method": "keyword",
                "query_preprocessing": "normalize",
            },
            "results": [
                {
                    "id": "doc-1",
                    "title": "Architecture Overview",
                    "text": "Hello from the retrieved chunk",
                    "chunk_length_tokens": 12,
                    "relevance_score": 0.987,
                    "relevance_kind": "keyword_score",
                    "metadata": {"document_id": "doc-1"},
                }
            ],
        },
    )

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/query",
        headers=_auth(token),
        json={"query_text": "hello", "top_k": 5, "search_method": "keyword", "query_preprocessing": "normalize"},
    )

    assert response.status_code == 200
    assert captured["knowledge_base_id"] == "kb-primary"
    assert captured["payload"] == {
        "query_text": "hello",
        "top_k": 5,
        "search_method": "keyword",
        "query_preprocessing": "normalize",
    }
    assert response.get_json()["retrieval"]["index"] == "kb_product_docs"
    assert response.get_json()["retrieval"]["search_method"] == "keyword"
    assert response.get_json()["retrieval"]["query_preprocessing"] == "normalize"
    assert response.get_json()["results"][0]["chunk_length_tokens"] == 12
    assert response.get_json()["results"][0]["relevance_score"] == 0.987
    assert response.get_json()["results"][0]["relevance_kind"] == "keyword_score"


def test_query_knowledge_base_route_accepts_hybrid_search_parameters(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-hybrid-query@example.com",
        username="admin-hybrid-query",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        context_routes,
        "query_knowledge_base",
        lambda *_args, **_kwargs: captured.update(_kwargs) or {
            "knowledge_base_id": "kb-primary",
            "retrieval": {
                "index": "kb_product_docs",
                "result_count": 1,
                "top_k": 5,
                "search_method": "hybrid",
                "query_preprocessing": "normalize",
                "hybrid_alpha": 0.65,
            },
            "results": [
                {
                    "id": "doc-2",
                    "title": "FAQ",
                    "text": "Hybrid retrieval result",
                    "chunk_length_tokens": 8,
                    "relevance_score": 0.812,
                    "relevance_kind": "hybrid_score",
                    "relevance_components": {"semantic_score": 0.74, "keyword_score": 0.95},
                    "metadata": {"document_id": "doc-2"},
                }
            ],
        },
    )

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/query",
        headers=_auth(token),
        json={
            "query_text": "raul",
            "top_k": 5,
            "search_method": "hybrid",
            "query_preprocessing": "normalize",
            "hybrid_alpha": 0.65,
        },
    )

    assert response.status_code == 200
    assert captured["knowledge_base_id"] == "kb-primary"
    assert captured["payload"] == {
        "query_text": "raul",
        "top_k": 5,
        "search_method": "hybrid",
        "query_preprocessing": "normalize",
        "hybrid_alpha": 0.65,
    }
    assert response.get_json()["retrieval"]["search_method"] == "hybrid"
    assert response.get_json()["retrieval"]["hybrid_alpha"] == 0.65
    assert response.get_json()["results"][0]["relevance_kind"] == "hybrid_score"
    assert response.get_json()["results"][0]["relevance_components"] == {
        "semantic_score": 0.74,
        "keyword_score": 0.95,
    }


def test_query_knowledge_base_route_accepts_metadata_filters(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-filter-query@example.com",
        username="admin-filter-query",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        context_routes,
        "query_knowledge_base",
        lambda *_args, **_kwargs: captured.update(_kwargs) or {
            "knowledge_base_id": "kb-primary",
            "retrieval": {
                "index": "kb_product_docs",
                "result_count": 1,
                "top_k": 5,
                "search_method": "semantic",
                "query_preprocessing": "none",
            },
            "results": [
                {
                    "id": "doc-filtered",
                    "title": "Filtered Result",
                    "text": "Filtered chunk",
                    "chunk_length_tokens": 9,
                    "relevance_score": 0.88,
                    "relevance_kind": "similarity",
                    "metadata": {"document_id": "doc-filtered", "category": "guide"},
                }
            ],
        },
    )

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/query",
        headers=_auth(token),
        json={
            "query_text": "hello",
            "filters": {
                "category": "guide",
                "page_count": 2,
                "published": True,
            },
        },
    )

    assert response.status_code == 200
    assert captured["payload"] == {
        "query_text": "hello",
        "filters": {
            "category": "guide",
            "page_count": 2,
            "published": True,
        },
    }
    assert response.get_json()["results"][0]["id"] == "doc-filtered"


def test_list_knowledge_sources_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-sources@example.com",
        username="admin-sources",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_knowledge_sources",
        lambda *_args, **_kwargs: [
            {
                "id": "source-1",
                "knowledge_base_id": "kb-primary",
                "source_type": "local_directory",
                "display_name": "Docs folder",
                "relative_path": "product_docs",
                "include_globs": ["**/*.md"],
                "exclude_globs": [],
                "lifecycle_state": "active",
                "last_sync_status": "ready",
            }
        ],
    )

    response = test_client.get("/v1/context/knowledge-bases/kb-primary/sources", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["sources"][0]["id"] == "source-1"


def test_create_knowledge_source_route_requires_superadmin(client):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-create-source@example.com",
        username="admin-create-source",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/sources",
        headers=_auth(token),
        json={"display_name": "Docs folder", "relative_path": "product_docs"},
    )

    assert response.status_code == 403


def test_create_knowledge_source_route_passes_metadata_for_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-create-source@example.com",
        username="superadmin-create-source",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    def _create_source(_db, *, config, knowledge_base_id: str, payload, created_by_user_id: int):
        captured["knowledge_base_id"] = knowledge_base_id
        captured["payload"] = payload
        captured["created_by_user_id"] = created_by_user_id
        return {
            "id": "source-1",
            "knowledge_base_id": knowledge_base_id,
            "source_type": "local_directory",
            "display_name": payload["display_name"],
            "relative_path": payload["relative_path"],
            "include_globs": [],
            "exclude_globs": [],
            "metadata": payload["metadata"],
            "lifecycle_state": "active",
            "last_sync_status": "idle",
        }

    monkeypatch.setattr(context_routes, "create_knowledge_source", _create_source)

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/sources",
        headers=_auth(token),
        json={
            "display_name": "Docs folder",
            "relative_path": "product_docs",
            "metadata": {"category": "guide"},
        },
    )

    assert response.status_code == 201
    assert captured["payload"] == {
        "display_name": "Docs folder",
        "relative_path": "product_docs",
        "metadata": {"category": "guide"},
    }
    assert response.get_json()["source"]["metadata"] == {"category": "guide"}


def test_sync_knowledge_source_route_returns_payload_for_superadmin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-sources@example.com",
        username="superadmin-sources",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "sync_knowledge_source",
        lambda *_args, **_kwargs: {
            "knowledge_base": {"id": "kb-primary", "display_name": "Product Docs"},
            "source": {"id": "source-1", "display_name": "Docs folder", "last_sync_status": "ready"},
            "sync_run": {"id": "run-1", "status": "ready", "created_document_count": 2},
        },
    )

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/sources/source-1/sync",
        headers=_auth(token),
    )

    assert response.status_code == 202
    assert response.get_json()["sync_run"]["id"] == "run-1"


def test_list_knowledge_base_sync_runs_route_returns_payload_for_admin(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    admin = users.create_user(
        "ignored",
        email="admin-sync-runs@example.com",
        username="admin-sync-runs",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        context_routes,
        "list_knowledge_base_sync_runs",
        lambda *_args, **_kwargs: [
            {
                "id": "run-1",
                "knowledge_base_id": "kb-primary",
                "source_id": "source-1",
                "source_display_name": "Docs folder",
                "status": "ready",
                "scanned_file_count": 5,
                "changed_file_count": 1,
                "deleted_file_count": 0,
                "created_document_count": 2,
                "updated_document_count": 1,
                "deleted_document_count": 0,
                "error_summary": None,
                "started_at": "2026-03-30T10:00:00+00:00",
                "finished_at": "2026-03-30T10:01:00+00:00",
            }
        ],
    )

    response = test_client.get("/v1/context/knowledge-bases/kb-primary/sync-runs", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["sync_runs"][0]["source_display_name"] == "Docs folder"


def test_upload_knowledge_base_documents_route_passes_multipart_metadata(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    superadmin = users.create_user(
        "ignored",
        email="superadmin-upload-docs@example.com",
        username="superadmin-upload-docs",
        password_hash=hash_password("superadmin-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, superadmin["username"], "superadmin-pass-123").get_json()["access_token"]
    captured: dict[str, object] = {}

    def _upload_documents(_db, *, config, knowledge_base_id: str, files, metadata, created_by_user_id: int):
        captured["knowledge_base_id"] = knowledge_base_id
        captured["metadata"] = metadata
        captured["file_names"] = [getattr(file, "filename", "") for file in files]
        captured["created_by_user_id"] = created_by_user_id
        return {"documents": [], "count": 0}

    monkeypatch.setattr(context_routes, "upload_knowledge_base_documents", _upload_documents)

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/uploads",
        headers=_auth(token),
        data={
            "metadata": '{"category":"guide","published":true}',
            "files": (io.BytesIO(b"hello"), "guide.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert captured["knowledge_base_id"] == "kb-primary"
    assert captured["metadata"] == {"category": "guide", "published": True}
    assert captured["file_names"] == ["guide.txt"]
