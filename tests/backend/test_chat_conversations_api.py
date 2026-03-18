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


def test_list_conversations_route_requires_auth(client):
    test_client, _users = client

    response = test_client.get("/v1/chat/conversations")

    assert response.status_code == 401


def test_send_message_route_returns_service_payload(client, monkeypatch: pytest.MonkeyPatch):
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
        "send_plain_message",
        lambda *_args, **_kwargs: {
            "conversation": {
                "id": "conv-1",
                "title": "Hello",
                "titleSource": "auto",
                "modelId": "safe-small",
                "messageCount": 2,
                "createdAt": "2026-03-18T11:00:00+00:00",
                "updatedAt": "2026-03-18T11:00:01+00:00",
            },
            "messages": [
                {"id": "msg-1", "role": "user", "content": "Hello", "metadata": {}, "createdAt": "2026-03-18T11:00:00+00:00"},
                {"id": "msg-2", "role": "assistant", "content": "Hi", "metadata": {}, "createdAt": "2026-03-18T11:00:01+00:00"},
            ],
            "output": "Hi",
        },
    )

    response = test_client.post(
        "/v1/chat/conversations/conv-1/messages",
        headers=_auth(token),
        json={"prompt": "Hello"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["conversation"]["messageCount"] == 2
    assert payload["messages"][1]["content"] == "Hi"


def test_get_conversation_route_returns_not_found(client, monkeypatch: pytest.MonkeyPatch):
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

    monkeypatch.setattr(chat_routes, "get_plain_conversation_detail", lambda *_args, **_kwargs: (_ for _ in ()).throw(chat_routes.ChatConversationNotFoundError()))

    response = test_client.get("/v1/chat/conversations/missing", headers=_auth(token))

    assert response.status_code == 404
    assert response.get_json()["error"] == "conversation_not_found"
