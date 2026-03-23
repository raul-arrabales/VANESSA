from __future__ import annotations

from typing import Any

import pytest

from app.routes import modelops as modelops_routes  # noqa: E402
from app.services import chat_inference  # noqa: E402
from app.services.modelops_common import ModelOpsError  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(modelops_routes, "_config", lambda: config)
    monkeypatch.setattr(chat_inference, "get_auth_config", lambda: config)
    yield test_client, user_store


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def test_user_lists_allowed_models_from_modelops_endpoint(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user1",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        modelops_routes,
        "list_models",
        lambda _db, **kwargs: [
            {
                "id": "allowed-model",
                "name": "Allowed Model",
                "provider": "hf-local",
                "backend": "local",
                "owner_type": "platform",
                "visibility_scope": "user",
                "task_key": "llm",
                "category": "generative",
                "lifecycle_state": "active",
                "is_validation_current": True,
                "last_validation_status": "success",
                "availability": "offline_ready",
            }
        ],
    )

    allowed = test_client.get("/v1/modelops/models", headers=_auth(token))
    assert allowed.status_code == 200
    assert [m["id"] for m in allowed.get_json()["models"]] == ["allowed-model"]


def test_generate_route_enforces_modelops_eligibility(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="user2@example.com",
        username="user2",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    def _ensure_model_invokable(_db: str, *, config, user_id: int, user_role: str, model_id: str):
        _ = (config, user_id, user_role)
        if model_id == "allowed-model":
            return {"id": model_id, "backend_kind": "local", "availability": "offline_ready"}
        raise ModelOpsError("forbidden", "Requested model is not allowed", status_code=403)

    monkeypatch.setattr(chat_inference, "ensure_model_invokable", _ensure_model_invokable)
    monkeypatch.setattr(
        chat_inference.modelops_repo,
        "get_model",
        lambda _db, model_id: {
            "model_id": model_id,
            "backend_kind": "local",
            "availability": "offline_ready",
        },
    )

    seen_payload: dict[str, Any] = {}

    class FakeAdapter:
        def __init__(self):
            self.binding = type(
                "Binding",
                (),
                {
                    "config": {"canonical_local_model_id": "allowed-model"},
                    "served_models": [
                        {
                            "id": "allowed-model",
                            "name": "Allowed Model",
                            "backend": "local",
                            "local_path": "allowed-model",
                        }
                    ],
                },
            )()

        def list_models(self):
            return {"data": [{"id": "allowed-model"}]}, 200

        def chat_completion(self, *, model, messages, max_tokens, temperature, allow_local_fallback):
            seen_payload.update(
                {
                    "model": model,
                    "input": messages,
                    "allow_local_fallback": allow_local_fallback,
                }
            )
            return {"output": [{"content": [{"type": "text", "text": "ok"}]}]}, 200

    monkeypatch.setattr(chat_inference, "resolve_llm_inference_adapter", lambda _db, _config: FakeAdapter())

    permitted = test_client.post(
        "/v1/models/generate",
        headers=_auth(token),
        json={"model_id": "allowed-model", "prompt": "hello"},
    )
    assert permitted.status_code == 200
    assert seen_payload["model"] == "allowed-model"
    assert seen_payload["input"][0]["role"] == "user"
    assert seen_payload["allow_local_fallback"] is True

    forbidden = test_client.post(
        "/v1/models/generate",
        headers=_auth(token),
        json={"model_id": "blocked-model", "prompt": "hello"},
    )
    assert forbidden.status_code == 403
    assert forbidden.get_json()["error"] == "forbidden"
