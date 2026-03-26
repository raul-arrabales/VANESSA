from __future__ import annotations

import pytest

from app.routes import context as context_routes  # noqa: E402
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
                "backing_provider_key": "weaviate_local",
                "lifecycle_state": "active",
                "sync_status": "ready",
                "schema": {},
                "document_count": 2,
                "binding_count": 1,
            }
        ],
    )

    response = test_client.get("/v1/context/knowledge-bases", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["knowledge_bases"][0]["id"] == "kb-primary"


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
