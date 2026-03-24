from __future__ import annotations

import pytest

from app.services import chat_inference  # noqa: E402
from app.services.modelops_common import ModelOpsError  # noqa: E402
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


def test_inference_returns_modelops_access_errors(client, monkeypatch: pytest.MonkeyPatch):
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
        "ensure_model_invokable",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ModelOpsError(
                "offline_not_allowed",
                "Model is not available in offline mode",
                status_code=409,
            )
        ),
    )

    response = test_client.post(
        "/v1/models/inference",
        headers=_auth(token),
        json={"model": "gpt-4o", "prompt": "hi"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "offline_not_allowed"


def test_inference_uses_canonical_local_llm_alias(client, monkeypatch: pytest.MonkeyPatch):
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
        "ensure_model_invokable",
        lambda *args, **kwargs: {
            "id": "Qwen--Qwen2.5-0.5B-Instruct",
            "backend_kind": "local",
            "availability": "offline_ready",
        },
    )
    monkeypatch.setattr(
        chat_inference.modelops_repo,
        "get_model",
        lambda _db, model_id: {
            "model_id": model_id,
            "backend_kind": "local",
            "availability": "offline_ready",
        },
    )

    class FakeAdapter:
        def __init__(self):
            self.calls: list[dict[str, object]] = []
            self.binding = type(
                "Binding",
                (),
                {
                    "resources": [
                        {
                            "id": "Qwen--Qwen2.5-0.5B-Instruct",
                            "resource_kind": "model",
                            "provider_resource_id": "local-vllm-default",
                            "display_name": "Qwen 0.5B",
                            "metadata": {
                                "backend": "local",
                                "local_path": "local-vllm-default",
                            },
                        }
                    ],
                    "config": {
                        "canonical_local_model_id": "local-vllm-default",
                        "local_fallback_model_id": "local-vllm-default",
                    },
                },
            )()

        def list_models(self):
            return {"data": [{"id": "local-vllm-default"}]}, 200

        def chat_completion(self, *, model, messages, max_tokens, temperature, allow_local_fallback):
            self.calls.append(
                {
                    "model": model,
                    "allow_local_fallback": allow_local_fallback,
                }
            )
            return {
                "output": [{"content": [{"type": "text", "text": "ok"}]}],
            }, 200

    adapter = FakeAdapter()
    monkeypatch.setattr(chat_inference, "resolve_llm_inference_adapter", lambda _db, _config: adapter)

    response = test_client.post(
        "/v1/models/inference",
        headers=_auth(token),
        json={"model": "Qwen--Qwen2.5-0.5B-Instruct", "prompt": "hi"},
    )

    assert response.status_code == 200
    assert response.get_json()["output"] == "ok"
    assert adapter.calls == [
        {
            "model": "local-vllm-default",
            "allow_local_fallback": True,
        }
    ]
