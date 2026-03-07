from __future__ import annotations

import pytest

from app.services import chat_inference  # noqa: E402
from app.services import model_resolution  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(chat_inference, "get_auth_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_inference_prompts_local_model_choice_when_external_unavailable_offline(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="off@example.com",
        username="offlineuser",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        chat_inference,
        "resolve_model_for_inference",
        lambda _db, *, user_id, requested_model_id: (
            None,
            {
                "error": "model_unavailable_offline",
                "message": "Requested model is external API-backed and unavailable in offline mode",
                "action": "choose_local_model",
                "available_local_models": ["phi-3-mini"],
            },
            409,
        ),
    )

    response = test_client.post(
        "/v1/models/inference",
        headers=_auth(token),
        json={"model": "gpt-4o", "prompt": "hi"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "model_unavailable_offline"
    assert response.get_json()["action"] == "choose_local_model"
    assert response.get_json()["available_local_models"] == ["phi-3-mini"]


def test_resolve_model_for_inference_returns_offline_fallback_for_external_models(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        model_resolution,
        "list_models_for_user",
        lambda _db, *, user_id: (
            "offline",
            [
                {
                    "model_id": "phi-3-mini",
                    "backend_kind": "local",
                    "availability": "offline_ready",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        model_resolution,
        "get_model_by_id",
        lambda _db, model_id: {
            "model_id": model_id,
            "backend_kind": "external_api",
            "availability": "online_only",
        },
    )

    resolved_model_id, error_payload, status_code = model_resolution.resolve_model_for_inference(
        "postgresql://ignored",
        user_id=7,
        requested_model_id="gpt-4o",
    )

    assert resolved_model_id is None
    assert status_code == 409
    assert error_payload == {
        "error": "model_unavailable_offline",
        "message": "Requested model is external API-backed and unavailable in offline mode",
        "action": "choose_local_model",
        "available_local_models": ["phi-3-mini"],
    }


def test_resolve_model_for_inference_returns_forbidden_when_not_visible(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        model_resolution,
        "list_models_for_user",
        lambda _db, *, user_id: (
            "online",
            [
                {
                    "model_id": "phi-3-mini",
                    "backend_kind": "local",
                    "availability": "offline_ready",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        model_resolution,
        "get_model_by_id",
        lambda _db, model_id: {
            "model_id": model_id,
            "backend_kind": "external_api",
            "availability": "online_only",
        },
    )

    resolved_model_id, error_payload, status_code = model_resolution.resolve_model_for_inference(
        "postgresql://ignored",
        user_id=7,
        requested_model_id="gpt-4o",
    )

    assert resolved_model_id is None
    assert status_code == 403
    assert error_payload == {
        "error": "model_forbidden",
        "message": "Requested model is not allowed",
    }


def test_inference_retries_local_llm_alias_when_upstream_model_not_found(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="local@example.com",
        username="localuser",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        chat_inference,
        "resolve_model_for_inference",
        lambda _db, *, user_id, requested_model_id: (requested_model_id, None, 200),
    )
    monkeypatch.setattr(
        chat_inference,
        "get_model_by_id",
        lambda _db, model_id: {
            "model_id": model_id,
            "backend_kind": "local",
            "availability": "offline_ready",
        },
    )

    calls: list[dict[str, object]] = []

    def fake_llm_request(_url: str, payload: dict[str, object]):
        calls.append(dict(payload))
        if payload.get("model") == "Qwen--Qwen2.5-0.5B-Instruct":
            return {"detail": {"code": "model_not_found", "message": "Unknown model"}}, 404
        if payload.get("model") == "local-vllm-default":
            return {
                "output": [{"content": [{"type": "text", "text": "ok"}]}],
            }, 200
        return {"detail": {"code": "unexpected_model"}}, 400

    monkeypatch.setattr(chat_inference, "http_json_request", fake_llm_request)

    response = test_client.post(
        "/v1/models/inference",
        headers=_auth(token),
        json={"model": "Qwen--Qwen2.5-0.5B-Instruct", "prompt": "hi"},
    )

    assert response.status_code == 200
    assert response.get_json()["output"] == "ok"
    assert [call.get("model") for call in calls] == [
        "Qwen--Qwen2.5-0.5B-Instruct",
        "local-vllm-default",
    ]
