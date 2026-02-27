from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.routes import registry_models as registry_models_routes  # noqa: E402
from app.routes import model_governance as model_governance_routes  # noqa: E402
from app.services import chat_inference  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


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
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    model_store = InMemoryModelAccessStore()

    monkeypatch.setattr(model_governance_routes, "find_model_definition", model_store.find_model)
    monkeypatch.setattr(model_governance_routes, "assign_model_access", model_store.assign)
    monkeypatch.setattr(model_governance_routes, "list_effective_allowed_models", model_store.effective)
    monkeypatch.setattr(model_governance_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(registry_models_routes, "_database_url", lambda: "ignored")
    monkeypatch.setattr(chat_inference, "get_auth_config", lambda: config)
    monkeypatch.setattr(chat_inference, "list_effective_allowed_models", model_store.effective)

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
        if entity_type not in {"model", "models"}:
            raise ValueError("invalid_entity_type")
        created = model_store.register_model(
            "ignored",
            model_id=entity_id,
            provider=str(spec.get("provider", "hf-local")),
            metadata=spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {},
            provider_config_ref=(
                str(spec.get("provider_config_ref")).strip()
                if spec.get("provider_config_ref") is not None
                else None
            ),
            created_by_user_id=owner_user_id,
        )
        return {
            "entity": {
                "entity_id": entity_id,
                "entity_type": "model",
                "owner_user_id": owner_user_id,
                "visibility": visibility,
                "status": "published" if publish else "draft",
                "current_version": version,
                "current_spec": spec,
            },
            "version": {"entity_id": entity_id, "version": version, "spec_json": created},
        }

    monkeypatch.setattr(registry_models_routes, "create_entity_with_version", _create_entity_with_version)

    yield test_client, user_store, model_store


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


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
        "/v1/registry/models",
        headers=_auth(super_token),
        json={
            "id": "gpt-private-1",
            "version": "v1",
            "visibility": "private",
            "publish": True,
            "spec": {
                "provider": "hf-local",
                "metadata": {"family": "gpt"},
                "provider_config_ref": "providers/hf-local/main",
            },
        },
    )
    assert created.status_code == 201
    assert created.get_json()["entity"]["entity_id"] == "gpt-private-1"

    forbidden = test_client.post(
        "/v1/registry/models",
        headers=_auth(admin_token),
        json={"id": "gpt-private-2", "spec": {"provider": "hf-local"}},
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
        "/v1/model-governance/access-assignments",
        headers=_auth(admin_token),
        json={
            "model_id": "gpt-private-allowed",
            "scope_type": "user",
            "scope_id": str(user["id"]),
        },
    )
    assert assigned.status_code == 201

    forbidden_manage = test_client.post(
        "/v1/model-governance/access-assignments",
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
        "/v1/model-governance/access-assignments",
        headers=_auth(admin_token),
        json={
            "model_id": "allowed-model",
            "scope_type": "user",
            "scope_id": str(user["id"]),
        },
    )

    allowed = test_client.get("/v1/model-governance/allowed", headers=_auth(user_token))
    assert allowed.status_code == 200
    assert [m["model_id"] for m in allowed.get_json()["models"]] == ["allowed-model"]

    seen_payload: dict[str, Any] = {}
    seen_url = ""

    def fake_llm_request(_url: str, payload: dict[str, Any]):
        nonlocal seen_url
        seen_url = _url
        seen_payload.update(payload)
        return {"ok": True, "model": payload["model"]}, 200

    monkeypatch.setattr(chat_inference, "http_json_request", fake_llm_request)

    permitted = test_client.post(
        "/v1/models/generate",
        headers=_auth(user_token),
        json={"model_id": "allowed-model", "prompt": "hello"},
    )
    assert permitted.status_code == 200
    assert seen_payload["model"] == "allowed-model"
    assert seen_payload["input"][0]["role"] == "user"
    assert seen_url.endswith(":8000/v1/chat/completions")

    forbidden = test_client.post(
        "/v1/models/generate",
        headers=_auth(user_token),
        json={"model_id": "blocked-model", "prompt": "hello"},
    )
    assert forbidden.status_code == 403
