from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.routes import model_management_v1 as routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, _config = backend_test_client_factory()

    credentials: dict[str, dict] = {}
    models: dict[str, dict] = {}

    def _create_credential(_db: str, **kwargs):
        now = datetime.now(tz=timezone.utc)
        identifier = str(uuid4())
        row = {
            "id": identifier,
            "owner_user_id": kwargs["owner_user_id"],
            "credential_scope": kwargs["credential_scope"],
            "provider_slug": kwargs["provider_slug"],
            "display_name": kwargs["display_name"],
            "api_base_url": kwargs.get("api_base_url"),
            "api_key_last4": kwargs["api_key"][-4:],
            "is_active": True,
            "created_by_user_id": kwargs["created_by_user_id"],
            "revoked_at": None,
            "created_at": now,
            "updated_at": now,
        }
        credentials[identifier] = {**row, "api_key": kwargs["api_key"]}
        return row

    def _list_credentials(_db: str, requester_user_id: int, requester_role: str):
        if requester_role == "superadmin":
            return [dict(value) for value in credentials.values() if value.get("is_active")]
        return [dict(value) for value in credentials.values() if value.get("owner_user_id") == requester_user_id and value.get("is_active")]

    def _revoke_credential(_db: str, credential_id: str, owner_user_id: int):
        item = credentials.get(credential_id)
        if not item or item.get("owner_user_id") != owner_user_id:
            return None
        item["is_active"] = False
        item["revoked_at"] = datetime.now(tz=timezone.utc)
        return dict(item)

    def _get_secret(_db: str, credential_id: str, requester_user_id: int, requester_role: str, encryption_key: str):
        item = credentials.get(credential_id)
        if not item:
            return None
        if requester_role != "superadmin" and item["owner_user_id"] != requester_user_id:
            return None
        return {
            "id": credential_id,
            "owner_user_id": item["owner_user_id"],
            "credential_scope": item["credential_scope"],
            "provider_slug": item["provider_slug"],
            "display_name": item["display_name"],
            "api_base_url": item["api_base_url"],
            "api_key": item["api_key"],
        }

    def _register_model(_db: str, **kwargs):
        now = datetime.now(tz=timezone.utc)
        row = {
            "model_id": kwargs["model_id"],
            "name": kwargs["name"],
            "provider": kwargs["provider"],
            "provider_model_id": kwargs.get("provider_model_id"),
            "origin_scope": kwargs["origin_scope"],
            "backend_kind": kwargs["backend_kind"],
            "source_kind": kwargs["source_kind"],
            "availability": kwargs["availability"],
            "access_scope": kwargs["access_scope"],
            "metadata": kwargs["metadata"],
            "model_size_billion": kwargs.get("model_size_billion"),
            "model_type": kwargs.get("model_type"),
            "comment": kwargs.get("comment"),
            "updated_at": now,
        }
        models[row["model_id"]] = row
        return row

    monkeypatch.setattr(routes, "create_credential", _create_credential)
    monkeypatch.setattr(routes, "list_credentials_for_user", _list_credentials)
    monkeypatch.setattr(routes, "revoke_credential", _revoke_credential)
    monkeypatch.setattr(routes, "get_active_credential_secret", _get_secret)
    monkeypatch.setattr(routes, "register_model", _register_model)
    monkeypatch.setattr(routes, "append_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes, "assign_model_to_user", lambda *args, **kwargs: {"model_id": kwargs["model_id"], "user_id": kwargs["user_id"]})
    monkeypatch.setattr(routes, "resolve_runtime_profile", lambda _db: "online")
    monkeypatch.setattr(routes, "list_models_visible_to_user", lambda _db, user_id, runtime_profile: list(models.values()))
    monkeypatch.setattr(routes, "validate_openai_compatible_model", lambda **kwargs: None)
    monkeypatch.setattr(routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(routes, "_encryption_key", lambda: "test-secret")

    yield test_client, user_store


def _auth(token: str):
    return auth_header(token)


def _token(client, username: str, password: str) -> str:
    return login(client, username, password).get_json()["access_token"]


def test_user_can_create_and_list_personal_credential(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="u@example.com",
        username="user",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _token(test_client, user["username"], "pass-123")

    created = test_client.post(
        "/v1/models/credentials",
        headers=_auth(token),
        json={"provider": "openai_compatible", "display_name": "my-key", "api_base_url": "https://api.example.com/v1", "api_key": "sk-user-secret"},
    )
    assert created.status_code == 201
    body = created.get_json()["credential"]
    assert body["api_key_last4"] == "cret"
    assert "api_key" not in body

    listed = test_client.get("/v1/models/credentials", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["credentials"][0]["display_name"] == "my-key"


def test_non_superadmin_cannot_create_platform_credential(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="u2@example.com",
        username="user2",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _token(test_client, user["username"], "pass-123")

    response = test_client.post(
        "/v1/models/credentials",
        headers=_auth(token),
        json={"credential_scope": "platform", "provider": "openai_compatible", "api_key": "sk-abc"},
    )
    assert response.status_code == 403


def test_register_external_model_requires_validation_path(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="u3@example.com",
        username="user3",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _token(test_client, user["username"], "pass-123")

    credential = test_client.post(
        "/v1/models/credentials",
        headers=_auth(token),
        json={"provider": "openai_compatible", "display_name": "my-key", "api_base_url": "https://api.example.com/v1", "api_key": "sk-user-secret"},
    ).get_json()["credential"]

    registered = test_client.post(
        "/v1/models/register",
        headers=_auth(token),
        json={
            "id": "gpt-4o-private",
            "name": "GPT 4o Private",
            "provider": "openai_compatible",
            "origin": "personal",
            "backend": "external_api",
            "provider_model_id": "gpt-4o",
            "credential_id": credential["id"],
            "access_scope": "private",
            "model_type": "llm",
        },
    )
    assert registered.status_code == 201
    model = registered.get_json()["model"]
    assert model["id"] == "gpt-4o-private"
    assert model["backend"] == "external_api"


def test_available_models_endpoint_returns_models(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="u4@example.com",
        username="user4",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _token(test_client, user["username"], "pass-123")

    test_client.post(
        "/v1/models/register",
        headers=_auth(token),
        json={
            "id": "phi-offline",
            "name": "Phi Offline",
            "provider": "local_filesystem",
            "origin": "personal",
            "backend": "local",
            "source": "local_folder",
            "availability": "offline_ready",
            "access_scope": "private",
            "model_type": "llm",
        },
    )

    listed = test_client.get("/v1/models/available", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["runtime_profile"] == "online"
    assert listed.get_json()["models"][0]["id"] == "phi-offline"


def test_register_model_requires_model_type(client):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="u5@example.com",
        username="user5",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    token = _token(test_client, user["username"], "pass-123")

    response = test_client.post(
        "/v1/models/register",
        headers=_auth(token),
        json={
            "id": "phi-offline",
            "name": "Phi Offline",
            "provider": "local_filesystem",
            "origin": "personal",
            "backend": "local",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_model_type"
