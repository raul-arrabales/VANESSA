from __future__ import annotations

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

    monkeypatch.setattr(
        context_routes,
        "query_knowledge_base",
        lambda *_args, **_kwargs: {
            "knowledge_base_id": "kb-primary",
            "retrieval": {"index": "kb_product_docs", "result_count": 1, "top_k": 5},
            "results": [{"id": "doc-1", "title": "Architecture Overview", "snippet": "Hello"}],
        },
    )

    response = test_client.post(
        "/v1/context/knowledge-bases/kb-primary/query",
        headers=_auth(token),
        json={"query_text": "hello", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.get_json()["retrieval"]["index"] == "kb_product_docs"


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

    assert response.status_code == 200
    assert response.get_json()["sync_run"]["id"] == "run-1"
