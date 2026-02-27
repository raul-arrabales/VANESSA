from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
        needle = identifier.strip().lower()
        for user in self.users.values():
            if user["email"] == needle or user["username"] == needle:
                return dict(user)
        return None

    def find_by_id(self, _database_url: str, user_id: int) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        return dict(user) if user else None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE", "online")
    user_store = InMemoryUserStore(users={})
    catalog: dict[str, dict[str, Any]] = {}
    assignments: dict[str, list[str]] = {"user": [], "admin": [], "superadmin": []}
    jobs: dict[str, dict[str, Any]] = {}

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
        model_storage_root="/models/llm",
        model_download_max_workers=1,
        model_download_stale_seconds=900,
        model_download_allow_patterns_default="",
        model_download_ignore_patterns_default="",
        hf_token="",
    )

    monkeypatch.setattr(backend_app_module, "_ensure_auth_initialized", lambda: True)
    monkeypatch.setattr(backend_app_module, "_get_config", lambda: config)
    monkeypatch.setattr(backend_app_module, "create_user", user_store.create_user)
    monkeypatch.setattr(backend_app_module, "find_user_by_identifier", user_store.find_by_identifier)
    monkeypatch.setattr(backend_app_module, "find_user_by_id", user_store.find_by_id)
    monkeypatch.setattr(backend_app_module, "_ensure_download_worker_started", lambda: None)
    monkeypatch.setattr(backend_app_module, "resolve_target_dir", lambda root, source_id: f"{root}/{source_id.replace('/', '--')}")

    def _list_catalog(_database_url: str):
        return list(catalog.values())

    def _create_catalog(
        _database_url: str,
        *,
        model_id: str,
        name: str,
        provider: str,
        source_id: str | None,
        local_path: str | None,
        status: str,
        metadata: dict[str, Any],
        created_by_user_id: int,
    ):
        if model_id in catalog:
            raise ValueError("duplicate_model")
        now = datetime.now(tz=timezone.utc)
        row = {
            "model_id": model_id,
            "name": name,
            "provider": provider,
            "source_id": source_id,
            "local_path": local_path,
            "status": status,
            "metadata": metadata,
            "created_at": now,
            "updated_at": now,
            "created_by_user_id": created_by_user_id,
        }
        catalog[model_id] = row
        return row

    def _upsert_catalog(
        _database_url: str,
        *,
        model_id: str,
        name: str,
        provider: str,
        source_id: str | None,
        local_path: str | None,
        status: str,
        metadata: dict[str, Any],
        updated_by_user_id: int | None = None,
    ):
        now = datetime.now(tz=timezone.utc)
        row = catalog.get(model_id, {})
        row.update(
            {
                "model_id": model_id,
                "name": name,
                "provider": provider,
                "source_id": source_id,
                "local_path": local_path,
                "status": status,
                "metadata": metadata,
                "created_at": row.get("created_at", now),
                "updated_at": now,
                "updated_by_user_id": updated_by_user_id,
            }
        )
        catalog[model_id] = row
        return row

    monkeypatch.setattr(backend_app_module, "list_model_catalog", _list_catalog)
    monkeypatch.setattr(backend_app_module, "create_model_catalog_item", _create_catalog)
    monkeypatch.setattr(backend_app_module, "upsert_model_catalog_item", _upsert_catalog)
    monkeypatch.setattr(backend_app_module, "get_model_catalog_item", lambda _db, model_id: catalog.get(model_id))

    monkeypatch.setattr(backend_app_module, "list_scope_assignments", lambda _db: [{"scope": k, "model_ids": v} for k, v in assignments.items()])
    monkeypatch.setattr(
        backend_app_module,
        "upsert_scope_assignment",
        lambda _db, *, scope, model_ids, updated_by_user_id: {"scope": scope, "model_ids": model_ids},
    )

    monkeypatch.setattr(
        backend_app_module,
        "discover_hf_models",
        lambda **kwargs: [
            {"source_id": "meta-llama/Llama-3-8B-Instruct", "name": "Llama-3-8B-Instruct", "downloads": 10, "likes": 1, "tags": ["text-generation"], "provider": "huggingface"}
        ],
    )
    monkeypatch.setattr(
        backend_app_module,
        "get_hf_model_details",
        lambda source_id, token=None: {
            "source_id": source_id,
            "name": source_id.split("/")[-1],
            "tags": ["text-generation"],
            "files": [{"path": "config.json", "size": 123}],
        },
    )

    def _create_job(_db: str, *, job_id: UUID, provider: str, source_id: str, target_dir: str, created_by_user_id: int):
        now = datetime.now(tz=timezone.utc)
        row = {
            "id": str(job_id),
            "provider": provider,
            "source_id": source_id,
            "target_dir": target_dir,
            "model_id": None,
            "status": "queued",
            "error_message": None,
            "created_by_user_id": created_by_user_id,
            "started_at": None,
            "finished_at": None,
            "created_at": now,
            "updated_at": now,
        }
        jobs[str(job_id)] = row
        return row

    monkeypatch.setattr(backend_app_module, "create_download_job", _create_job)
    monkeypatch.setattr(backend_app_module, "get_download_job", lambda _db, job_id: jobs.get(job_id))
    monkeypatch.setattr(backend_app_module, "list_download_jobs", lambda _db, status=None, limit=50: list(jobs.values()))

    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client, user_store


def _login(client, identifier: str, password: str):
    return client.post("/auth/login", json={"identifier": identifier, "password": password})


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_superadmin_catalog_discovery_and_download_apis(client):
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

    created = test_client.post(
        "/models/catalog",
        headers=_auth(token),
        json={"id": "llama-3-8b", "name": "Llama 3 8B", "provider": "huggingface", "source_id": "meta-llama/Llama-3-8B-Instruct"},
    )
    assert created.status_code == 201
    assert created.get_json()["model"]["id"] == "llama-3-8b"

    listed = test_client.get("/models/catalog", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["models"][0]["id"] == "llama-3-8b"

    discovered = test_client.get("/models/discovery/huggingface?query=llama", headers=_auth(token))
    assert discovered.status_code == 200
    assert discovered.get_json()["models"][0]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    details = test_client.get("/models/discovery/huggingface/meta-llama/Llama-3-8B-Instruct", headers=_auth(token))
    assert details.status_code == 200
    assert details.get_json()["model"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    download = test_client.post(
        "/models/catalog/downloads",
        headers=_auth(token),
        json={"source_id": "meta-llama/Llama-3-8B-Instruct", "name": "Llama 3 8B"},
    )
    assert download.status_code == 202
    job_id = download.get_json()["job"]["job_id"]

    fetched = test_client.get(f"/models/catalog/downloads/{job_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.get_json()["job"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"


def test_admin_can_manage_assignments_but_user_cannot(client):
    test_client, user_store = client
    admin = user_store.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    user = user_store.create_user(
        "ignored",
        email="user@example.com",
        username="user",
        password_hash=hash_password("user-pass-123"),
        role="user",
        is_active=True,
    )
    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    user_token = _login(test_client, user["username"], "user-pass-123").get_json()["access_token"]

    updated = test_client.put(
        "/models/assignments",
        headers=_auth(admin_token),
        json={"scope": "user", "model_ids": ["model-a", "model-b"]},
    )
    assert updated.status_code == 200
    assert updated.get_json()["assignment"]["scope"] == "user"

    forbidden = test_client.put(
        "/models/assignments",
        headers=_auth(user_token),
        json={"scope": "user", "model_ids": ["model-a"]},
    )
    assert forbidden.status_code == 403
