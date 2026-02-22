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
        normalized_email = email.strip().lower()
        normalized_username = username.strip().lower()

        for user in self.users.values():
            if user["email"] == normalized_email or user["username"] == normalized_username:
                raise ValueError("duplicate_user")

        now = datetime.now(tz=timezone.utc)
        user = {
            "id": self.next_id,
            "email": normalized_email,
            "username": normalized_username,
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

    def activate(self, _database_url: str, user_id: int) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user["is_active"] = True
        user["updated_at"] = datetime.now(tz=timezone.utc)
        return dict(user)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    store = InMemoryUserStore(users={})
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
    monkeypatch.setattr(backend_app_module, "create_user", store.create_user)
    monkeypatch.setattr(backend_app_module, "find_user_by_identifier", store.find_by_identifier)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", store.find_by_id)
    monkeypatch.setattr(backend_app_module, "activate_user", store.activate)

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, store


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str):
    return client.post(
        "/auth/login",
        json={"identifier": identifier, "password": password},
    )


def test_self_registration_creates_inactive_user(client):
    test_client, _ = client
    response = test_client.post(
        "/auth/register",
        json={"email": "u1@example.com", "username": "u1", "password": "password123"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["role"] == "user"
    assert payload["user"]["is_active"] is False


def test_non_superadmin_cannot_assign_elevated_role(client):
    test_client, _ = client
    response = test_client.post(
        "/auth/register",
        json={
            "email": "u2@example.com",
            "username": "u2",
            "password": "password123",
            "role": "admin",
        },
    )

    assert response.status_code == 403


def test_superadmin_can_create_elevated_roles(client):
    test_client, store = client
    superadmin = store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )

    token = _login(test_client, "root", "root-pass-123").get_json()["access_token"]
    response = test_client.post(
        "/auth/register",
        headers=_auth_header(token),
        json={
            "email": "admin@example.com",
            "username": "admin1",
            "password": "password123",
            "role": "admin",
            "is_active": True,
        },
    )

    assert superadmin["role"] == "superadmin"
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "admin"


def test_login_success_and_wrong_password(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="active@example.com",
        username="active",
        password_hash=hash_password("good-pass-123"),
        role="user",
        is_active=True,
    )

    success = _login(test_client, "active", "good-pass-123")
    assert success.status_code == 200
    assert success.get_json()["token_type"] == "bearer"

    bad = _login(test_client, "active", "wrong-password")
    assert bad.status_code == 401


def test_inactive_user_login_rejected(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="inactive@example.com",
        username="inactive",
        password_hash=hash_password("inactive-pass"),
        role="user",
        is_active=False,
    )

    response = _login(test_client, "inactive", "inactive-pass")
    assert response.status_code == 403


def test_auth_required_endpoint_rejects_without_token(client):
    test_client, _ = client
    response = test_client.get("/auth/me")
    assert response.status_code == 401


def test_insufficient_role_rejected_on_superadmin_route(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, "admin", "admin-pass-123").get_json()["access_token"]

    response = test_client.get("/superadmin/ping", headers=_auth_header(token))
    assert response.status_code == 403


def test_correct_role_allowed_on_protected_route(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="adminok@example.com",
        username="adminok",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = _login(test_client, "adminok", "admin-pass-123").get_json()["access_token"]

    response = test_client.get("/admin/ping", headers=_auth_header(token))
    assert response.status_code == 200


def test_activation_policy_for_admin_and_superadmin(client):
    test_client, store = client
    admin = store.create_user(
        "ignored",
        email="admina@example.com",
        username="admina",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    superadmin = store.create_user(
        "ignored",
        email="super@example.com",
        username="super",
        password_hash=hash_password("super-pass-123"),
        role="superadmin",
        is_active=True,
    )
    pending_user = store.create_user(
        "ignored",
        email="pending-user@example.com",
        username="pendinguser",
        password_hash=hash_password("pending-pass-123"),
        role="user",
        is_active=False,
    )
    pending_admin = store.create_user(
        "ignored",
        email="pending-admin@example.com",
        username="pendingadmin",
        password_hash=hash_password("pending-pass-123"),
        role="admin",
        is_active=False,
    )

    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    super_token = _login(test_client, superadmin["username"], "super-pass-123").get_json()["access_token"]

    can_activate_user = test_client.post(
        f"/auth/users/{pending_user['id']}/activate",
        headers=_auth_header(admin_token),
    )
    assert can_activate_user.status_code == 200
    assert can_activate_user.get_json()["user"]["is_active"] is True

    cannot_activate_admin = test_client.post(
        f"/auth/users/{pending_admin['id']}/activate",
        headers=_auth_header(admin_token),
    )
    assert cannot_activate_admin.status_code == 403

    superadmin_can_activate_admin = test_client.post(
        f"/auth/users/{pending_admin['id']}/activate",
        headers=_auth_header(super_token),
    )
    assert superadmin_can_activate_admin.status_code == 200
    assert superadmin_can_activate_admin.get_json()["user"]["is_active"] is True
