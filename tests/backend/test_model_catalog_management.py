from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.api.http import modelops as modelops_routes  # noqa: E402
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

    def _upsert_model(_database_url: str, **kwargs):
        now = datetime.now(tz=timezone.utc)
        row = {
            "model_id": kwargs["model_id"],
            "name": kwargs["name"],
            "provider": kwargs["provider"],
            "source_id": kwargs.get("source_id"),
            "local_path": kwargs.get("local_path"),
            "status": kwargs["status"],
            "task_key": kwargs["task_key"],
            "category": kwargs["category"],
            "hosting_kind": "local",
            "lifecycle_state": kwargs["lifecycle_state"],
            "is_validation_current": False,
            "last_validation_status": None,
            "metadata": kwargs["metadata"],
            "created_at": catalog.get(kwargs["model_id"], {}).get("created_at", now),
            "updated_at": now,
        }
        catalog[row["model_id"]] = row
        return row

    monkeypatch.setattr(modelops_routes, "_config", lambda: config)
    monkeypatch.setattr(modelops_routes.modelops_repo, "list_catalog_models", _list_catalog)
    monkeypatch.setattr(
        modelops_routes.modelops_repo,
        "list_local_artifacts",
        lambda _db: [
            {
                "model_id": model_id,
                "name": row["name"],
                "source_id": row.get("source_id"),
                "task_key": row["task_key"],
                "category": row["category"],
                "lifecycle_state": row["lifecycle_state"],
                "provider": row["provider"],
                "metadata": row["metadata"],
                "artifact_type": "weights",
                "storage_path": row.get("local_path"),
                "artifact_status": "ready" if row.get("local_path") else "missing",
                "provenance": row.get("source_id"),
                "checksum": None,
                "runtime_requirements": {},
            }
            for model_id, row in catalog.items()
            if row.get("local_path")
        ],
    )
    monkeypatch.setattr(modelops_routes.modelops_repo, "upsert_model_record", _upsert_model)
    monkeypatch.setattr(modelops_routes.modelops_repo, "append_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(modelops_routes, "list_scope_assignments", lambda _db: [{"scope": k, "model_ids": v} for k, v in assignments.items()])
    monkeypatch.setattr(
        modelops_routes,
        "upsert_scope_assignment",
        lambda _db, *, scope, model_ids, updated_by_user_id: {"scope": scope, "model_ids": model_ids},
    )
    monkeypatch.setattr(
        modelops_routes,
        "discover_hf_models",
        lambda **kwargs: [
            {
                "source_id": "meta-llama/Llama-3-8B-Instruct",
                "name": "Llama-3-8B-Instruct",
                "downloads": 10,
                "likes": 1,
                "tags": ["text-generation"],
                "provider": "huggingface",
            }
        ],
    )
    monkeypatch.setattr(
        modelops_routes,
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

    monkeypatch.setattr(modelops_routes, "create_download_job", _create_job)
    monkeypatch.setattr(modelops_routes, "get_download_job", lambda _db, job_id: jobs.get(job_id))
    monkeypatch.setattr(modelops_routes, "list_download_jobs", lambda _db, status=None, limit=50: list(jobs.values()))
    monkeypatch.setattr(modelops_routes, "ensure_download_worker_started", lambda: None)

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
        "/v1/modelops/catalog",
        headers=_auth(token),
        json={"id": "llama-3-8b", "name": "Llama 3 8B", "provider": "huggingface", "source_id": "meta-llama/Llama-3-8B-Instruct", "task_key": "llm"},
    )
    assert created.status_code == 201
    assert created.get_json()["model"]["id"] == "llama-3-8b"

    listed = test_client.get("/v1/modelops/catalog", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["models"][0]["id"] == "llama-3-8b"

    discovered = test_client.get("/v1/modelops/discovery/huggingface?query=llama", headers=_auth(token))
    assert discovered.status_code == 200
    assert discovered.get_json()["models"][0]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    details = test_client.get("/v1/modelops/discovery/huggingface/meta-llama/Llama-3-8B-Instruct", headers=_auth(token))
    assert details.status_code == 200
    assert details.get_json()["model"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"

    download = test_client.post(
        "/v1/modelops/downloads",
        headers=_auth(token),
        json={"source_id": "meta-llama/Llama-3-8B-Instruct", "name": "Llama 3 8B", "task_key": "llm"},
    )
    assert download.status_code == 202
    job_id = download.get_json()["job"]["job_id"]

    fetched = test_client.get(f"/v1/modelops/downloads/{job_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.get_json()["job"]["source_id"] == "meta-llama/Llama-3-8B-Instruct"


def test_hf_discovery_uses_embedding_task_for_embedding_task_key(client, monkeypatch: pytest.MonkeyPatch):
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

    monkeypatch.setattr(modelops_routes, "discover_hf_models", _discover)

    response = test_client.get(
        "/v1/modelops/discovery/huggingface?query=embed&task_key=embeddings",
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert captured["task"] == "feature-extraction"


def test_superadmin_can_list_local_artifacts(client):
    test_client, user_store = client
    root = user_store.create_user(
        "ignored",
        email="root3@example.com",
        username="root3",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    create_response = test_client.post(
        "/v1/modelops/catalog",
        headers=_auth(token),
        json={
            "id": "phi-local",
            "name": "Phi Local",
            "provider": "local",
            "local_path": "/models/llm/phi-local",
            "task_key": "llm",
        },
    )
    assert create_response.status_code == 201

    listed = test_client.get("/v1/modelops/local-artifacts", headers=_auth(token))
    assert listed.status_code == 200
    artifact = listed.get_json()["artifacts"][0]
    assert artifact["artifact_id"] == "phi-local:weights"
    assert artifact["linked_model_id"] == "phi-local"
    assert artifact["ready_for_registration"] is False


def test_admin_can_manage_sharing_but_user_cannot(client):
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
        "/v1/modelops/sharing",
        headers=_auth(admin_token),
        json={"scope": "user", "model_ids": ["model-a", "model-b"]},
    )
    assert updated.status_code == 200
    assert updated.get_json()["assignment"]["scope"] == "user"

    forbidden = test_client.put(
        "/v1/modelops/sharing",
        headers=_auth(user_token),
        json={"scope": "user", "model_ids": ["model-a"]},
    )
    assert forbidden.status_code == 403
