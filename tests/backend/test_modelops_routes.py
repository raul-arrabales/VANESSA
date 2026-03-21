from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.routes import modelops as routes  # noqa: E402
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

    def _create_model(_db: str, **kwargs):
        if not kwargs["payload"].get("task_key"):
            raise routes.ModelOpsError("missing_config", "task_key is required", status_code=400)
        now = datetime.now(tz=timezone.utc)
        row = {
            "model_id": kwargs["payload"]["id"],
            "name": kwargs["payload"]["name"],
            "provider": kwargs["payload"]["provider"],
            "provider_model_id": kwargs["payload"].get("provider_model_id"),
            "backend_kind": kwargs["payload"]["backend"],
            "owner_type": kwargs["payload"].get("owner_type", "user"),
            "visibility_scope": kwargs["payload"].get("visibility_scope", "private"),
            "availability": kwargs["payload"].get("availability", "online_only"),
            "task_key": kwargs["payload"]["task_key"],
            "category": kwargs["payload"].get("category", "generative"),
            "updated_at": now,
        }
        models[row["model_id"]] = row
        return {
            "id": row["model_id"],
            "name": row["name"],
            "provider": row["provider"],
            "provider_model_id": row["provider_model_id"],
            "backend": row["backend_kind"],
            "owner_type": row["owner_type"],
            "visibility_scope": row["visibility_scope"],
            "availability": row["availability"],
            "task_key": row["task_key"],
            "category": row["category"],
        }

    monkeypatch.setattr(routes, "create_credential", _create_credential)
    monkeypatch.setattr(routes, "list_credentials_for_user", _list_credentials)
    monkeypatch.setattr(routes, "revoke_credential", _revoke_credential)
    monkeypatch.setattr(routes, "create_model", _create_model)
    monkeypatch.setattr(routes.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        routes,
        "list_models",
        lambda _db, **kwargs: [
            {
                "id": row["model_id"],
                "name": row["name"],
                "provider": row["provider"],
                "backend": row["backend_kind"],
                "owner_type": row["owner_type"],
                "visibility_scope": row["visibility_scope"],
                "availability": row["availability"],
                "task_key": row["task_key"],
                "category": row["category"],
            }
            for row in models.values()
        ],
    )
    monkeypatch.setattr(routes, "_config", lambda: _config)

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
        "/v1/modelops/credentials",
        headers=_auth(token),
        json={"provider": "openai_compatible", "display_name": "my-key", "api_base_url": "https://api.example.com/v1", "api_key": "sk-user-secret"},
    )
    assert created.status_code == 201
    body = created.get_json()["credential"]
    assert body["api_key_last4"] == "cret"
    assert "api_key" not in body

    listed = test_client.get("/v1/modelops/credentials", headers=_auth(token))
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
        "/v1/modelops/credentials",
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
        "/v1/modelops/credentials",
        headers=_auth(token),
        json={"provider": "openai_compatible", "display_name": "my-key", "api_base_url": "https://api.example.com/v1", "api_key": "sk-user-secret"},
    ).get_json()["credential"]

    registered = test_client.post(
        "/v1/modelops/models",
        headers=_auth(token),
        json={
            "id": "gpt-4o-private",
            "name": "GPT 4o Private",
            "provider": "openai_compatible",
            "backend": "external_api",
            "provider_model_id": "gpt-4o",
            "credential_id": credential["id"],
            "visibility_scope": "private",
            "task_key": "llm",
            "category": "generative",
        },
    )
    assert registered.status_code == 201
    model = registered.get_json()["model"]
    assert model["id"] == "gpt-4o-private"
    assert model["backend"] == "external_api"


def test_modelops_models_endpoint_returns_models(client):
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
        "/v1/modelops/models",
        headers=_auth(token),
        json={
            "id": "phi-offline",
            "name": "Phi Offline",
            "provider": "local_filesystem",
            "backend": "local",
            "source": "local_folder",
            "availability": "offline_ready",
            "visibility_scope": "private",
            "task_key": "llm",
            "category": "generative",
        },
    )

    listed = test_client.get("/v1/modelops/models", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["models"][0]["id"] == "phi-offline"


def test_admin_can_test_model_and_user_cannot(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    admin = user_store.create_user(
        "ignored",
        email="admin@example.com",
        username="admin-user",
        password_hash=hash_password("pass-123"),
        role="admin",
        is_active=True,
    )
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="plain-user",
        password_hash=hash_password("pass-123"),
        role="user",
        is_active=True,
    )
    admin_token = _token(test_client, admin["username"], "pass-123")
    user_token = _token(test_client, user["username"], "pass-123")

    monkeypatch.setattr(
        routes,
        "run_model_test",
        lambda _db, **kwargs: {
            "model": {"id": kwargs["model_id"], "name": "GPT 4o"},
            "test_run": {"id": "test-run-1", "result": "success"},
            "result": {"kind": "llm", "success": True, "response_text": "hello"},
        },
    )

    admin_response = test_client.post(
        "/v1/modelops/models/gpt-4o/test",
        headers=_auth(admin_token),
        json={"inputs": {"prompt": "hello"}},
    )
    assert admin_response.status_code == 200
    assert admin_response.get_json()["test_run"]["id"] == "test-run-1"

    user_response = test_client.post(
        "/v1/modelops/models/gpt-4o/test",
        headers=_auth(user_token),
        json={"inputs": {"prompt": "hello"}},
    )
    assert user_response.status_code == 403


def test_validate_route_requires_test_run_id(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    admin = user_store.create_user(
        "ignored",
        email="admin2@example.com",
        username="admin-two",
        password_hash=hash_password("pass-123"),
        role="admin",
        is_active=True,
    )
    admin_token = _token(test_client, admin["username"], "pass-123")

    monkeypatch.setattr(
        routes,
        "validate_model",
        lambda _db, **kwargs: {
            "model": {"id": kwargs["model_id"]},
            "validation": {"result": "success", "error_details": {"test_run_id": kwargs["test_run_id"]}},
        },
    )

    response = test_client.post(
        "/v1/modelops/models/gpt-4o/validate",
        headers=_auth(admin_token),
        json={"test_run_id": "test-run-1"},
    )
    assert response.status_code == 200
    assert response.get_json()["validation"]["error_details"] == {"test_run_id": "test-run-1"}


def test_create_model_requires_task_key(client):
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
        "/v1/modelops/models",
        headers=_auth(token),
        json={
            "id": "phi-offline",
            "name": "Phi Offline",
            "provider": "local_filesystem",
            "backend": "local",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "missing_config"
