from __future__ import annotations

import sys
from dataclasses import dataclass, field
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

    def find_by_identifier(
        self, _database_url: str, identifier: str
    ) -> dict[str, Any] | None:
        normalized = identifier.strip().lower()
        for user in self.users.values():
            if user["email"] == normalized or user["username"] == normalized:
                return dict(user)
        return None

    def find_by_id(self, _database_url: str, user_id: int) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        return dict(user) if user else None


@dataclass
class InMemoryModelAccessStore:
    models: dict[str, dict[str, Any]] = field(default_factory=dict)
    assignments: list[dict[str, str]] = field(default_factory=list)

    def register_model(
        self,
        _database_url: str,
        *,
        model_id: str,
        provider: str,
        metadata: dict[str, Any],
        provider_config_ref: str | None,
        created_by_user_id: int,
    ) -> dict[str, Any]:
        if model_id in self.models:
            raise ValueError("duplicate_model")
        model = {
            "model_id": model_id,
            "provider": provider,
            "metadata": dict(metadata),
            "provider_config_ref": provider_config_ref,
            "created_by_user_id": created_by_user_id,
        }
        self.models[model_id] = model
        return dict(model)

    def find_model(self, _database_url: str, model_id: str) -> dict[str, Any] | None:
        model = self.models.get(model_id)
        return dict(model) if model else None

    def assign(
        self,
        _database_url: str,
        *,
        model_id: str,
        scope_type: str,
        scope_id: str,
        assigned_by_user_id: int,
    ) -> dict[str, Any]:
        assignment = {
            "model_id": model_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "assigned_by_user_id": str(assigned_by_user_id),
        }
        self.assignments = [
            a
            for a in self.assignments
            if not (
                a["model_id"] == model_id
                and a["scope_type"] == scope_type
                and a["scope_id"] == scope_id
            )
        ]
        self.assignments.append(assignment)
        return dict(assignment)

    def effective(
        self,
        _database_url: str,
        *,
        user_id: int,
        org_id: str | None,
        group_id: str | None,
    ) -> list[dict[str, Any]]:
        model_ids = set()
        for assignment in self.assignments:
            if assignment["scope_type"] == "user" and assignment["scope_id"] == str(
                user_id
            ):
                model_ids.add(assignment["model_id"])
            if (
                org_id
                and assignment["scope_type"] == "org"
                and assignment["scope_id"] == org_id
            ):
                model_ids.add(assignment["model_id"])
            if (
                group_id
                and assignment["scope_type"] == "group"
                and assignment["scope_id"] == group_id
            ):
                model_ids.add(assignment["model_id"])

        return [dict(self.models[model_id]) for model_id in sorted(model_ids)]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    user_store = InMemoryUserStore(users={})
    model_store = InMemoryModelAccessStore()
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
    monkeypatch.setattr(
        backend_app_module, "find_user_by_identifier", user_store.find_by_identifier
    )
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)

    monkeypatch.setattr(
        backend_app_module, "register_model_definition", model_store.register_model
    )
    monkeypatch.setattr(
        backend_app_module, "find_model_definition", model_store.find_model
    )
    monkeypatch.setattr(backend_app_module, "assign_model_access", model_store.assign)
    monkeypatch.setattr(
        backend_app_module, "list_effective_allowed_models", model_store.effective
    )

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store, model_store


def _login(client, identifier: str, password: str):
    return client.post(
        "/auth/login", json={"identifier": identifier, "password": password}
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_superadmin_can_register_model_and_admin_cannot(client):
    test_client, user_store, _ = client
    superadmin = user_store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    admin = user_store.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )

    super_token = _login(
        test_client, superadmin["username"], "root-pass-123"
    ).get_json()["access_token"]
    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()[
        "access_token"
    ]

    created = test_client.post(
        "/models/registry",
        headers=_auth(super_token),
        json={
            "model_id": "gpt-private-1",
            "provider": "hf-local",
            "metadata": {"family": "gpt"},
            "provider_config_ref": "providers/hf-local/main",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["model"]["model_id"] == "gpt-private-1"

    forbidden = test_client.post(
        "/models/registry",
        headers=_auth(admin_token),
        json={"model_id": "gpt-private-2", "provider": "hf-local"},
    )
    assert forbidden.status_code == 403


def test_admin_can_assign_model_access_but_user_cannot_manage(client):
    test_client, user_store, model_store = client
    superadmin = user_store.create_user(
        "ignored",
        email="root2@example.com",
        username="root2",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    admin = user_store.create_user(
        "ignored",
        email="admin2@example.com",
        username="admin2",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user1",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )

    model_store.register_model(
        "ignored",
        model_id="gpt-private-allowed",
        provider="hf-local",
        metadata={},
        provider_config_ref=None,
        created_by_user_id=superadmin["id"],
    )

    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()[
        "access_token"
    ]
    user_token = _login(test_client, user["username"], "user-pass-123").get_json()[
        "access_token"
    ]

    assigned = test_client.post(
        "/models/access-assignments",
        headers=_auth(admin_token),
        json={
            "model_id": "gpt-private-allowed",
            "scope_type": "user",
            "scope_id": str(user["id"]),
        },
    )
    assert assigned.status_code == 201

    forbidden_manage = test_client.post(
        "/models/access-assignments",
        headers=_auth(user_token),
        json={
            "model_id": "gpt-private-allowed",
            "scope_type": "user",
            "scope_id": str(user["id"]),
        },
    )
    assert forbidden_manage.status_code == 403


def test_user_reads_effective_allowed_models_and_generate_enforces_rbac(
    client, monkeypatch: pytest.MonkeyPatch
):
    test_client, user_store, model_store = client
    superadmin = user_store.create_user(
        "ignored",
        email="root3@example.com",
        username="root3",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    admin = user_store.create_user(
        "ignored",
        email="admin3@example.com",
        username="admin3",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    user = user_store.create_user(
        "ignored",
        email="user3@example.com",
        username="user3",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )

    model_store.register_model(
        "ignored",
        model_id="allowed-model",
        provider="hf-local",
        metadata={"size": "7b"},
        provider_config_ref="providers/hf-local/7b",
        created_by_user_id=superadmin["id"],
    )
    model_store.register_model(
        "ignored",
        model_id="blocked-model",
        provider="hf-local",
        metadata={},
        provider_config_ref=None,
        created_by_user_id=superadmin["id"],
    )

    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()[
        "access_token"
    ]
    user_token = _login(test_client, user["username"], "user-pass-123").get_json()[
        "access_token"
    ]

    test_client.post(
        "/models/access-assignments",
        headers=_auth(admin_token),
        json={
            "model_id": "allowed-model",
            "scope_type": "user",
            "scope_id": str(user["id"]),
        },
    )

    allowed = test_client.get("/models/allowed", headers=_auth(user_token))
    assert allowed.status_code == 200
    assert [m["model_id"] for m in allowed.get_json()["models"]] == ["allowed-model"]

    seen_payload: dict[str, Any] = {}

    def fake_llm_request(_url: str, payload: dict[str, Any]):
        seen_payload.update(payload)
        return {"ok": True, "model": payload["model"]}, 200

    monkeypatch.setattr(backend_app_module, "_http_json_request", fake_llm_request)

    permitted = test_client.post(
        "/llm/generate",
        headers=_auth(user_token),
        json={"model_id": "allowed-model", "prompt": "hello"},
    )
    assert permitted.status_code == 200
    assert seen_payload["model"] == "allowed-model"
    assert seen_payload["input"][0]["role"] == "user"

    forbidden = test_client.post(
        "/llm/generate",
        headers=_auth(user_token),
        json={"model_id": "blocked-model", "prompt": "hello"},
    )
    assert forbidden.status_code == 403
