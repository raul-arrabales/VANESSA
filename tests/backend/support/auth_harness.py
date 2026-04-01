from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


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

    def activate(self, _database_url: str, user_id: int) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user["is_active"] = True
        user["updated_at"] = datetime.now(tz=timezone.utc)
        return dict(user)

    def update_role(self, _database_url: str, user_id: int, role: str) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user["role"] = role
        user["updated_at"] = datetime.now(tz=timezone.utc)
        return dict(user)

    def list_users(self, _database_url: str, *, is_active: bool | None = None) -> list[dict[str, Any]]:
        users = list(self.users.values())
        if is_active is not None:
            users = [user for user in users if user["is_active"] is is_active]
        users.sort(key=lambda user: int(user["id"]))
        return [dict(user) for user in users]

    def count_by_role(self, _database_url: str, role: str) -> int:
        return sum(1 for user in self.users.values() if user["role"] == role)


def build_test_auth_config(auth_config_cls, **overrides):
    defaults = dict(
        database_url="postgresql://ignored",
        jwt_secret="test-secret-key-with-at-least-32-bytes",
        model_credentials_encryption_key="test-credential-secret-key-with-at-least-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=28_800,
        allow_self_register=True,
        bootstrap_superadmin_email="",
        bootstrap_superadmin_username="",
        bootstrap_superadmin_password="",
        flask_env="development",
    )
    defaults.update(overrides)
    return auth_config_cls(**defaults)


def patch_auth_bootstrap(
    monkeypatch,
    *,
    config,
    user_store: InMemoryUserStore,
    backend_app_module,
    auth_handler_module,
    extra_patches: dict[str, Any] | None = None,
):
    monkeypatch.setattr(backend_app_module, "_ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(backend_app_module, "_ensure_backend_initialized", lambda: True)
    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)

    monkeypatch.setattr(auth_handler_module, "get_config", lambda: config)
    monkeypatch.setattr(auth_handler_module, "auth_ready_or_503", lambda _json_error: None)
    monkeypatch.setattr(auth_handler_module, "create_user", user_store.create_user)
    monkeypatch.setattr(auth_handler_module, "find_user_by_identifier", user_store.find_by_identifier)
    monkeypatch.setattr(auth_handler_module, "find_user_by_id", user_store.find_by_id)

    if hasattr(auth_handler_module, "activate_user"):
        monkeypatch.setattr(auth_handler_module, "activate_user", user_store.activate)
    if hasattr(auth_handler_module, "update_user_role"):
        monkeypatch.setattr(auth_handler_module, "update_user_role", user_store.update_role)
    if hasattr(auth_handler_module, "list_users"):
        monkeypatch.setattr(auth_handler_module, "list_users", user_store.list_users)
    if hasattr(auth_handler_module, "count_users_by_role"):
        monkeypatch.setattr(auth_handler_module, "count_users_by_role", user_store.count_by_role)

    if extra_patches:
        for dotted_target, value in extra_patches.items():
            monkeypatch.setattr(dotted_target, value)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})
