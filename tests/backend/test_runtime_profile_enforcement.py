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
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE", raising=False)

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
    monkeypatch.setattr(backend_app_module, "create_user", user_store.create_user)
    monkeypatch.setattr(backend_app_module, "find_user_by_identifier", user_store.find_by_identifier)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)
    monkeypatch.setattr(backend_app_module, "discover_hf_models", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not call")))

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


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

    response = test_client.get("/models/discovery/huggingface?query=llama", headers=_auth(token))
    assert response.status_code == 403
    assert response.get_json()["error"] == "runtime_profile_blocks_internet"
