from __future__ import annotations

import pytest

from app.routes import model_catalog_v1 as model_catalog_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE", raising=False)
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(model_catalog_routes, "_config", lambda: config)
    monkeypatch.setattr(model_catalog_routes, "discover_hf_models", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not call")))
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_discovery_blocked_in_offline_profile(client):
    test_client, user_store = client
    root = user_store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    response = test_client.get("/v1/models/discovery/huggingface?query=llama", headers=_auth(token))
    assert response.status_code == 403
    assert response.get_json()["error"] == "runtime_profile_blocks_internet"
