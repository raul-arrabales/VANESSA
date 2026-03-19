from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.routes import model_catalog_v1 as model_catalog_routes  # noqa: E402
from app.routes import model_governance as model_governance_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VANESSA_RUNTIME_PROFILE_FORCE", "online")
    test_client, user_store, config = backend_test_client_factory(
        config_overrides={
            "model_storage_root": "/models/llm",
            "model_download_max_workers": 1,
            "model_download_stale_seconds": 900,
            "model_download_allow_patterns_default": "",
            "model_download_ignore_patterns_default": "",
            "hf_token": "",
        }
    )
    catalog: dict[str, dict[str, Any]] = {}
    assignments: dict[str, list[str]] = {"user": [], "admin": [], "superadmin": []}
    jobs: dict[str, dict[str, Any]] = {}

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
        model_type: str,
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
            "model_type": model_type,
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
        model_type: str,
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
                "model_type": model_type,
                "metadata": metadata,
                "created_at": row.get("created_at", now),
                "updated_at": now,
                "updated_by_user_id": updated_by_user_id,
            }
        )
        catalog[model_id] = row
        return row

    monkeypatch.setattr(model_catalog_routes, "list_model_catalog", _list_catalog)
    monkeypatch.setattr(model_catalog_routes, "create_model_catalog_item", _create_catalog)
    monkeypatch.setattr(model_catalog_routes, "upsert_model_catalog_item", _upsert_catalog)
    monkeypatch.setattr(model_catalog_routes, "_config", lambda: config)

    monkeypatch.setattr(model_governance_routes, "list_scope_assignments", lambda _db: [{"scope": k, "model_ids": v} for k, v in assignments.items()])
    monkeypatch.setattr(
        model_governance_routes,
        "upsert_scope_assignment",
        lambda _db, *, scope, model_ids, updated_by_user_id: {"scope": scope, "model_ids": model_ids},
    )
    monkeypatch.setattr(model_governance_routes, "_database_url", lambda: "ignored")

    monkeypatch.setattr(
        model_catalog_routes,
        "discover_hf_models",
        lambda **kwargs: [
            {"source_id": "meta-llama/Llama-3-8B-Instruct", "name": "Llama-3-8B-Instruct", "downloads": 10, "likes": 1, "tags": ["text-generation"], "provider": "huggingface"}
        ],
    )
    monkeypatch.setattr(
        model_catalog_routes,
        "get_hf_model_details",
        lambda source_id, database_url, token=None: {
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

    monkeypatch.setattr(model_catalog_routes, "create_download_job", _create_job)
    monkeypatch.setattr(model_catalog_routes, "get_download_job", lambda _db, job_id: jobs.get(job_id))
    monkeypatch.setattr(model_catalog_routes, "list_download_jobs", lambda _db, status=None, limit=50: list(jobs.values()))
    monkeypatch.setattr(model_catalog_routes, "ensure_download_worker_started", lambda: None)

    yield test_client, user_store


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


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
        "/v1/models/catalog",
        headers=_auth(token),
        json={"id": "llama-3-8b", "name": "Llama 3 8B", "provider": "huggingface", "source_id": "meta-llama/Llama-3-8B-Instruct", "model_type": "llm"},
    )
    assert created.status_code == 201
    assert created.get_json()["model"]["id"] == "llama-3-8b"

    listed = test_client.get("/v1/models/catalog", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["models"][0]["id"] == "llama-3-8b"

    discovered = test_client.get("/v1/models/discovery/huggingface?query=llama", headers=_auth(token))
    assert discovered.status_code == 200
    assert discovered.get_json()["models"][0]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    details = test_client.get("/v1/models/discovery/huggingface/meta-llama/Llama-3-8B-Instruct", headers=_auth(token))
    assert details.status_code == 200
    assert details.get_json()["model"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    download = test_client.post(
        "/v1/models/downloads",
        headers=_auth(token),
        json={"source_id": "meta-llama/Llama-3-8B-Instruct", "name": "Llama 3 8B", "model_type": "llm"},
    )
    assert download.status_code == 202
    job_id = download.get_json()["job"]["job_id"]

    fetched = test_client.get(f"/v1/models/downloads/{job_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.get_json()["job"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"


def test_hf_discovery_uses_embedding_task_for_embedding_model_type(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    root = user_store.create_user(
        "ignored",
        email="root2@example.com",
        username="root2",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]
    captured: dict[str, Any] = {}

    def _discover(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(model_catalog_routes, "discover_hf_models", _discover)

    response = test_client.get(
        "/v1/models/discovery/huggingface?query=embed&model_type=embedding",
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert captured["task"] == "feature-extraction"


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
        "/v1/model-governance/assignments",
        headers=_auth(admin_token),
        json={"scope": "user", "model_ids": ["model-a", "model-b"]},
    )
    assert updated.status_code == 200
    assert updated.get_json()["assignment"]["scope"] == "user"

    forbidden = test_client.put(
        "/v1/model-governance/assignments",
        headers=_auth(user_token),
        json={"scope": "user", "model_ids": ["model-a"]},
    )
    assert forbidden.status_code == 403


def test_enabled_models_endpoint_includes_scope_assigned_models(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    user = user_store.create_user(
        "ignored",
        email="viewer@example.com",
        username="viewer",
        password_hash=hash_password("viewer-pass-123"),
        role="user",
        is_active=True,
    )
    token = _login(test_client, user["username"], "viewer-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        model_governance_routes,
        "list_models_for_user",
        lambda _db, *, user_id: (
            "offline",
            [
                {
                    "model_id": "Qwen--Qwen2.5-0.5B-Instruct",
                    "name": "Qwen2.5-0.5B-Instruct",
                    "provider": "huggingface",
                    "metadata": {"description": "Offline local model"},
                    "backend_kind": "local",
                    "availability": "offline_ready",
                    "origin_scope": "platform",
                }
            ],
        ),
    )

    response = test_client.get("/v1/model-governance/enabled", headers=_auth(token))
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runtime_profile"] == "offline"
    assert payload["models"] == [
        {
            "id": "Qwen--Qwen2.5-0.5B-Instruct",
            "name": "Qwen2.5-0.5B-Instruct",
            "provider": "huggingface",
            "description": "Offline local model",
            "backend": "local",
            "availability": "offline_ready",
            "origin": "platform",
        }
    ]
