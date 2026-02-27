from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

import app.app as backend_app_module  # noqa: E402
from app.app import app  # noqa: E402
from app.config import AuthConfig  # noqa: E402
from app.handlers import auth_handlers as auth_handler  # noqa: E402
from app.routes import executions as executions_routes  # noqa: E402
from app.routes import registry as registry_routes  # noqa: E402
from app.routes import registry_models as registry_models_routes  # noqa: E402
from app.routes import runtime as runtime_routes  # noqa: E402
from app.security import hash_password  # noqa: E402


@dataclass
class InMemoryUserStore:
    users: dict[int, dict[str, Any]]
    next_id: int = 1

    def create_user(
        self,
        _database_url: str,
        *,
        email: str,
        username: str,
        password_hash: str,
        role: str,
        is_active: bool,
    ) -> dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        user = {
            "id": self.next_id,
            "email": email.strip().lower(),
            "username": username.strip().lower(),
            "password_hash": password_hash,
            "role": role,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        }
        self.users[self.next_id] = user
        self.next_id += 1
        return dict(user)

    def find_by_identifier(self, _database_url: str, identifier: str) -> dict[str, Any] | None:
        normalized = identifier.strip().lower()
        for user in self.users.values():
            if user["email"] == normalized or user["username"] == normalized:
                return dict(user)
        return None

    def find_by_id(self, _database_url: str, user_id: int) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        return dict(user) if user else None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    user_store = InMemoryUserStore(users={})
    config = AuthConfig(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )

    registry_items: dict[str, dict[str, Any]] = {}
    shares_by_entity: dict[str, list[dict[str, Any]]] = {}

    monkeypatch.setattr(backend_app_module, "_ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(auth_handler, "get_config", lambda: config)
    monkeypatch.setattr(auth_handler, "auth_ready_or_503", lambda _json_error: None)
    monkeypatch.setattr(auth_handler, "create_user", user_store.create_user)
    monkeypatch.setattr(auth_handler, "find_user_by_identifier", user_store.find_by_identifier)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)

    monkeypatch.setattr(registry_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(registry_models_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(runtime_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(executions_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(executions_routes, "_config", lambda: config)

    def _create_entity_with_version(
        _database_url: str,
        *,
        entity_type: str,
        entity_id: str,
        owner_user_id: int,
        visibility: str,
        spec: dict[str, Any],
        version: str,
        publish: bool,
    ) -> dict[str, Any]:
        item = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "owner_user_id": owner_user_id,
            "visibility": visibility,
            "status": "published" if publish else "draft",
            "current_version": version,
            "current_spec": spec,
        }
        registry_items[f"{entity_type}:{entity_id}"] = item
        return {
            "entity": item,
            "version": {"entity_id": entity_id, "version": version, "spec_json": spec},
        }

    def _list_entities(_database_url: str, *, entity_type: str) -> list[dict[str, Any]]:
        return [item for item in registry_items.values() if item["entity_type"] == entity_type]

    def _get_entity(_database_url: str, *, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        return registry_items.get(f"{entity_type}:{entity_id}")

    def _get_entity_versions(_database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
        for item in registry_items.values():
            if item["entity_id"] == entity_id:
                return [{"entity_id": entity_id, "version": item["current_version"], "spec_json": item["current_spec"]}]
        return []

    def _create_entity_version(
        _database_url: str,
        *,
        entity_type: str,
        entity_id: str,
        version: str,
        spec: dict[str, Any],
        publish: bool,
    ) -> dict[str, Any]:
        item = registry_items[f"{entity_type}:{entity_id}"]
        item["current_version"] = version
        item["current_spec"] = spec
        item["status"] = "published" if publish else "draft"
        return {
            "entity": item,
            "version": {"entity_id": entity_id, "version": version, "spec_json": spec},
        }

    def _grant_share(
        _database_url: str,
        *,
        current_user: dict[str, Any],
        entity: dict[str, Any],
        grantee_type: str,
        grantee_id: str | None,
        permission: str,
    ) -> dict[str, Any]:
        share = {
            "entity_id": entity["entity_id"],
            "grantee_type": grantee_type,
            "grantee_id": grantee_id,
            "permission": permission,
            "shared_by_user_id": current_user["id"],
        }
        shares_by_entity.setdefault(entity["entity_id"], []).append(share)
        return share

    monkeypatch.setattr(registry_routes, "create_entity_with_version", _create_entity_with_version)
    monkeypatch.setattr(registry_models_routes, "create_entity_with_version", _create_entity_with_version)
    monkeypatch.setattr(registry_routes, "list_entities", _list_entities)
    monkeypatch.setattr(registry_models_routes, "list_entities", _list_entities)
    monkeypatch.setattr(registry_routes, "get_entity", _get_entity)
    monkeypatch.setattr(registry_models_routes, "get_entity", _get_entity)
    monkeypatch.setattr(registry_routes, "get_entity_versions", _get_entity_versions)
    monkeypatch.setattr(registry_models_routes, "get_entity_versions", _get_entity_versions)
    monkeypatch.setattr(registry_routes, "create_entity_version", _create_entity_version)
    monkeypatch.setattr(registry_models_routes, "create_entity_version", _create_entity_version)
    monkeypatch.setattr(registry_routes, "grant_share", _grant_share)
    monkeypatch.setattr(registry_models_routes, "grant_share", _grant_share)
    monkeypatch.setattr(registry_routes, "get_shares", lambda _db, *, entity_id: shares_by_entity.get(entity_id, []))
    monkeypatch.setattr(registry_models_routes, "get_shares", lambda _db, *, entity_id: shares_by_entity.get(entity_id, []))

    monkeypatch.setattr(runtime_routes, "resolve_runtime_profile", lambda _db: "offline")
    monkeypatch.setattr(runtime_routes, "update_runtime_profile", lambda _db, *, profile, updated_by_user_id: profile)

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


def test_registry_and_runtime_endpoints(client):
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

    create_response = test_client.post(
        "/v1/registry/agents",
        headers=_auth(token),
        json={
            "id": "agent.alpha",
            "version": "v1",
            "visibility": "private",
            "publish": False,
            "spec": {
                "name": "Agent Alpha",
                "description": "test agent",
                "instructions": "be concise",
                "default_model_ref": "model.default",
                "tool_refs": [],
                "runtime_constraints": {"internet_required": False, "sandbox_required": True},
            },
        },
    )
    assert create_response.status_code == 201

    list_response = test_client.get("/v1/registry/agents", headers=_auth(token))
    assert list_response.status_code == 200
    assert list_response.get_json()["items"][0]["entity_id"] == "agent.alpha"

    share_response = test_client.post(
        "/v1/registry/agents/agent.alpha/share",
        headers=_auth(token),
        json={"grantee_type": "public", "permission": "view"},
    )
    assert share_response.status_code == 201

    runtime_get = test_client.get("/v1/runtime/profile")
    assert runtime_get.status_code == 200
    assert runtime_get.get_json()["profile"] == "offline"

    runtime_set = test_client.put(
        "/v1/runtime/profile",
        headers=_auth(token),
        json={"profile": "air_gapped"},
    )
    assert runtime_set.status_code == 200
    assert runtime_set.get_json()["profile"] == "air_gapped"


def test_agent_execution_proxy_endpoints(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        executions_routes,
        "create_execution",
        lambda **kwargs: (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": kwargs["agent_id"],
                    "agent_version": "v1",
                    "model_ref": None,
                    "runtime_profile": kwargs["runtime_profile"],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "result": {"output_text": "ok"},
                    "error": None,
                }
            },
            201,
        ),
    )
    monkeypatch.setattr(
        executions_routes,
        "get_execution",
        lambda **_kwargs: (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": "agent.alpha",
                    "agent_version": "v1",
                    "model_ref": None,
                    "runtime_profile": "offline",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "result": {"output_text": "ok"},
                    "error": None,
                }
            },
            200,
        ),
    )
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")

    create_response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.alpha", "input": {"prompt": "hi"}},
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["execution"]["id"] == "exec-1"

    get_response = test_client.get("/v1/agent-executions/exec-1", headers=_auth(token))
    assert get_response.status_code == 200
    assert get_response.get_json()["execution"]["status"] == "succeeded"
