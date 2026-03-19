from __future__ import annotations

import pytest

from app.routes import chat as chat_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(chat_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(chat_routes, "_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_knowledge_chat_route_requires_auth(client):
    test_client, _users = client

    response = test_client.post("/v1/chat/knowledge", json={"prompt": "hello", "model": "safe-small"})

    assert response.status_code == 401


def test_knowledge_chat_route_returns_service_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u1@example.com",
        username="u1",
        password_hash=hash_password("u1-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u1-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        chat_routes,
        "run_knowledge_chat",
        lambda **kwargs: (
            {
                "output": "answer",
                "response": {"id": "exec-knowledge"},
                "sources": [{"id": "doc-1", "title": "Doc 1", "snippet": "snippet", "metadata": {}}],
                "retrieval": {"index": "knowledge_base", "result_count": 1},
            },
            200,
        ),
    )

    response = test_client.post(
        "/v1/chat/knowledge",
        headers=_auth(token),
        json={"prompt": "hello", "model": "safe-small", "history": [{"role": "user", "content": "Earlier"}]},
    )

    assert response.status_code == 200
    assert response.get_json()["output"] == "answer"


def test_knowledge_chat_route_returns_json_on_unexpected_failure(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u2@example.com",
        username="u2",
        password_hash=hash_password("u2-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u2-pass-123").get_json()["access_token"]

    def _raise_unexpected(**_kwargs):
        raise RuntimeError("missing registry table")

    monkeypatch.setattr(chat_routes, "run_knowledge_chat", _raise_unexpected)

    response = test_client.post(
        "/v1/chat/knowledge",
        headers=_auth(token),
        json={"prompt": "hello", "model": "safe-small"},
    )

    assert response.status_code == 500
    assert response.is_json is True
    assert response.get_json() == {
        "error": "knowledge_chat_failed",
        "message": "Knowledge chat request failed.",
    }
