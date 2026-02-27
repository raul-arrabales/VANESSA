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
from app.handlers import legacy_auth as legacy_auth_handler  # noqa: E402
from app.routes import executions as executions_routes  # noqa: E402
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

    monkeypatch.setattr(backend_app_module, "_ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(legacy_auth_handler, "get_config", lambda: config)
    monkeypatch.setattr(legacy_auth_handler, "auth_ready_or_503", lambda _json_error: None)
    monkeypatch.setattr(legacy_auth_handler, "create_user", user_store.create_user)
    monkeypatch.setattr(legacy_auth_handler, "find_user_by_identifier", user_store.find_by_identifier)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)
    monkeypatch.setattr(executions_routes, "_database_url", lambda: "ignored")

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


def test_agent_execution_requires_registered_agent(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u@example.com",
        username="u",
        password_hash=hash_password("u-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u-pass-123").get_json()["access_token"]

    monkeypatch.setattr(executions_routes, "get_entity", lambda *_args, **_kwargs: None)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.unknown", "input": {"prompt": "x"}},
    )
    assert response.status_code == 404
    assert response.get_json()["error"] == "agent_not_found"


def test_agent_execution_permission_and_runtime_checks(client, monkeypatch: pytest.MonkeyPatch):
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

    agent = {
        "entity_id": "agent.internet",
        "owner_user_id": 999,
        "current_spec": {
            "runtime_constraints": {"internet_required": True}
        },
    }
    monkeypatch.setattr(executions_routes, "get_entity", lambda *_args, **_kwargs: agent)
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")

    def _deny(*, database_url: str, current_user: dict[str, Any], entity_id: str, required_permission: str):
        raise executions_routes.PolicyDeniedError("no execute")

    monkeypatch.setattr(executions_routes, "require_entity_permission", _deny)

    denied = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.internet", "input": {}},
    )
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "policy_denied"

    monkeypatch.setattr(executions_routes, "require_entity_permission", lambda **kwargs: None)
    blocked = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.internet", "input": {}},
    )
    assert blocked.status_code == 403
    assert blocked.get_json()["error"] == "runtime_profile_blocks_internet"


def test_agent_execution_success_proxy(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u3@example.com",
        username="u3",
        password_hash=hash_password("u3-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u3-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        executions_routes,
        "get_entity",
        lambda *_args, **_kwargs: {"entity_id": "agent.local", "owner_user_id": user["id"], "current_spec": {"runtime_constraints": {"internet_required": False}}},
    )
    monkeypatch.setattr(executions_routes, "require_entity_permission", lambda **kwargs: None)
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")
    monkeypatch.setattr(
        executions_routes,
        "_http_json_request",
        lambda url, payload: ({"execution": {"id": "exec-1", "agent_id": payload["agent_id"], "runtime_profile": payload["runtime_profile"]}}, 201),
    )

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello"}},
    )
    assert response.status_code == 201
    payload = response.get_json()["execution"]
    assert payload["id"] == "exec-1"
    assert payload["runtime_profile"] == "offline"


def test_agent_execution_blocks_non_offline_tool(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u4@example.com",
        username="u4",
        password_hash=hash_password("u4-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u4-pass-123").get_json()["access_token"]

    def _get_entity(_db: str, *, entity_type: str, entity_id: str):
        if entity_type == "agent":
            return {
                "entity_id": entity_id,
                "owner_user_id": user["id"],
                "current_spec": {
                    "runtime_constraints": {"internet_required": False},
                    "tool_refs": ["tool.remote"],
                },
            }
        if entity_type == "tool":
            return {
                "entity_id": entity_id,
                "current_spec": {"offline_compatible": False},
            }
        return None

    monkeypatch.setattr(executions_routes, "get_entity", _get_entity)
    monkeypatch.setattr(executions_routes, "require_entity_permission", lambda **kwargs: None)
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello"}},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "runtime_profile_blocks_tool"
