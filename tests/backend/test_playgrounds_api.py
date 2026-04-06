from __future__ import annotations

import pytest

from app.api.http import playgrounds as playground_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(playground_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(playground_routes, "_config", lambda: config)
    monkeypatch.setattr(playground_routes, "_request_id", lambda: "req-playground")
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _session_detail(
    session_id: str = "sess-1",
    *,
    playground_kind: str = "chat",
    model_id: str | None = "safe-small",
    knowledge_base_id: str | None = None,
) -> dict[str, object]:
    return {
        "id": session_id,
        "playground_kind": playground_kind,
        "assistant_ref": "agent.knowledge_chat" if playground_kind == "knowledge" else "assistant.playground.chat",
        "title": "Knowledge session" if playground_kind == "knowledge" else "Chat session",
        "title_source": "auto",
        "model_selection": {"model_id": model_id},
        "knowledge_binding": {"knowledge_base_id": knowledge_base_id},
        "message_count": 0,
        "created_at": "2026-03-18T11:00:00+00:00",
        "updated_at": "2026-03-18T11:00:00+00:00",
        "messages": [],
    }


def test_list_playground_sessions_requires_auth(client):
    test_client, _users = client

    response = test_client.get("/v1/playgrounds/sessions?playground_kind=chat")

    assert response.status_code == 401


def test_create_playground_session_returns_service_payload(client, monkeypatch: pytest.MonkeyPatch):
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

    monkeypatch.setattr(
        playground_routes,
        "create_playground_session",
        lambda *_args, **_kwargs: _session_detail("sess-new", playground_kind="knowledge", knowledge_base_id="kb-primary"),
    )

    response = test_client.post(
        "/v1/playgrounds/sessions",
        headers=_auth(token),
        json={
            "playground_kind": "knowledge",
            "model_selection": {"model_id": "safe-small"},
            "knowledge_binding": {"knowledge_base_id": "kb-primary"},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["session"]["playground_kind"] == "knowledge"
    assert payload["session"]["knowledge_binding"]["knowledge_base_id"] == "kb-primary"


def test_get_playground_session_route_returns_not_found(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="missing@example.com",
        username="missing",
        password_hash=hash_password("missing-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "missing-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        playground_routes,
        "get_playground_session_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(playground_routes.PlaygroundSessionNotFoundError()),
    )

    response = test_client.get(
        "/v1/playgrounds/sessions/missing?playground_kind=knowledge",
        headers=_auth(token),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "session_not_found"


def test_post_playground_message_route_returns_service_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="msg@example.com",
        username="msg-user",
        password_hash=hash_password("msg-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "msg-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        playground_routes,
        "send_playground_message",
        lambda *_args, **_kwargs: {
            "session": _session_detail("sess-1", playground_kind="knowledge", knowledge_base_id="kb-primary"),
            "messages": [
                {"id": "m1", "role": "user", "content": "hello", "metadata": {}, "createdAt": "2026-03-18T11:00:00+00:00"},
                {"id": "m2", "role": "assistant", "content": "answer", "metadata": {"sources": []}, "createdAt": "2026-03-18T11:00:01+00:00"},
            ],
            "output": "answer",
            "sources": [],
            "retrieval": {"index": "knowledge_base", "result_count": 0},
        },
    )

    response = test_client.post(
        "/v1/playgrounds/sessions/sess-1/messages",
        headers=_auth(token),
        json={"prompt": "hello"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["output"] == "answer"
    assert payload["session"]["id"] == "sess-1"
    assert payload["messages"][1]["content"] == "answer"


def test_stream_playground_message_route_returns_sse_events(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="stream@example.com",
        username="stream-user",
        password_hash=hash_password("stream-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "stream-pass-123").get_json()["access_token"]

    def _fake_stream(*_args, **_kwargs):
        yield {"event": "delta", "data": {"text": "Hello"}}
        yield {
            "event": "complete",
            "data": {
                "session": _session_detail("sess-1"),
                "messages": [
                    {"id": "m1", "role": "user", "content": "Hello", "metadata": {}, "createdAt": "2026-03-18T11:00:00+00:00"},
                    {"id": "m2", "role": "assistant", "content": "Hi", "metadata": {}, "createdAt": "2026-03-18T11:00:01+00:00"},
                ],
                "output": "Hi",
            },
        }

    monkeypatch.setattr(playground_routes, "stream_playground_message", _fake_stream)

    response = test_client.post(
        "/v1/playgrounds/sessions/sess-1/messages/stream",
        headers=_auth(token),
        json={"prompt": "Hello"},
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: delta" in body
    assert '"text": "Hello"' in body
    assert "event: complete" in body
    assert '"output": "Hi"' in body


def test_get_playground_options_route_returns_configuration_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="options@example.com",
        username="options-user",
        password_hash=hash_password("options-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "options-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        playground_routes,
        "get_playground_options",
        lambda *_args, **_kwargs: {
            "assistants": [],
            "models": [{"id": "safe-small", "display_name": "Safe Small"}],
            "knowledge_bases": [{"id": "kb-primary", "display_name": "Product Docs", "index_name": "kb_product_docs", "is_default": True}],
            "default_knowledge_base_id": "kb-primary",
            "selection_required": False,
            "configuration_message": None,
        },
    )

    response = test_client.get("/v1/playgrounds/options", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["default_knowledge_base_id"] == "kb-primary"


def test_get_playground_model_options_route_returns_lightweight_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="model-options@example.com",
        username="model-options-user",
        password_hash=hash_password("options-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "options-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        playground_routes,
        "get_playground_model_options",
        lambda *_args, **_kwargs: {
            "assistants": [{"assistant_ref": "assistant.playground.chat", "playground_kind": "chat"}],
            "models": [{"id": "safe-small", "display_name": "Safe Small", "task_key": "llm"}],
        },
    )

    response = test_client.get("/v1/playgrounds/model-options?playground_kind=chat", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["models"][0]["display_name"] == "Safe Small"


def test_get_playground_knowledge_base_options_route_returns_payload(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="knowledge-options@example.com",
        username="knowledge-options-user",
        password_hash=hash_password("options-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "options-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        playground_routes,
        "get_playground_knowledge_base_options",
        lambda *_args, **_kwargs: {
            "knowledge_bases": [{"id": "kb-primary", "display_name": "Product Docs", "index_name": "kb_product_docs", "is_default": True}],
            "default_knowledge_base_id": "kb-primary",
            "selection_required": False,
            "configuration_message": None,
        },
    )

    response = test_client.get("/v1/playgrounds/knowledge-base-options", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json()["knowledge_bases"][0]["id"] == "kb-primary"
