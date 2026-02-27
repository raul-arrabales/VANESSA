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
from app.services.agent_engine_client import AgentEngineClientError  # noqa: E402


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
    monkeypatch.setattr(executions_routes, "_config", lambda: config)
    monkeypatch.setattr(executions_routes, "resolve_runtime_profile", lambda _db: "offline")

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


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

    def _create_execution(**kwargs):
        assert kwargs["agent_id"] == "agent.local"
        assert kwargs["runtime_profile"] == "offline"
        assert kwargs["requested_by_user_id"] == user["id"]
        return (
            {
                "execution": {
                    "id": "exec-1",
                    "status": "succeeded",
                    "agent_ref": "agent.local",
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
            201,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": {"prompt": "hello"}},
    )
    assert response.status_code == 201
    payload = response.get_json()["execution"]
    assert payload["id"] == "exec-1"
    assert payload["runtime_profile"] == "offline"


def test_agent_execution_passes_engine_errors(client, monkeypatch: pytest.MonkeyPatch):
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

    def _create_execution(**_kwargs):
        raise AgentEngineClientError(
            code="EXEC_RUNTIME_PROFILE_BLOCKED",
            message="Blocked in offline profile",
            status_code=403,
        )

    monkeypatch.setattr(executions_routes, "create_execution", _create_execution)

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.internet", "input": {}},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "EXEC_RUNTIME_PROFILE_BLOCKED"


def test_agent_execution_invalid_input(client):
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

    response = test_client.post(
        "/v1/agent-executions",
        headers=_auth(token),
        json={"agent_id": "agent.local", "input": "bad"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_input"


def test_get_agent_execution_proxy(client, monkeypatch: pytest.MonkeyPatch):
    test_client, users = client
    user = users.create_user(
        "ignored",
        email="u5@example.com",
        username="u5",
        password_hash=hash_password("u5-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "u5-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        executions_routes,
        "get_execution",
        lambda **_kwargs: (
            {
                "execution": {
                    "id": "exec-5",
                    "status": "succeeded",
                    "agent_ref": "agent.local",
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
    response = test_client.get("/v1/agent-executions/exec-5", headers=_auth(token))
    assert response.status_code == 200
    assert response.get_json()["execution"]["id"] == "exec-5"
