from __future__ import annotations

import pytest

from app.application import registry_management_service


def test_create_registry_entity_requires_json_object() -> None:
    with pytest.raises(registry_management_service.RegistryManagementRequestError) as exc_info:
        registry_management_service.create_registry_entity_request(
            "postgresql://ignored",
            entity_type="agent",
            payload=[],
            owner_user_id=11,
        )

    assert exc_info.value.code == "invalid_payload"


def test_create_registry_entity_version_enforces_manage_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        registry_management_service,
        "get_entity",
        lambda *_args, **_kwargs: {"entity_id": "agent.alpha", "owner_user_id": 99},
    )
    monkeypatch.setattr(registry_management_service, "can_manage_entity", lambda **_kwargs: False)

    with pytest.raises(registry_management_service.RegistryManagementRequestError) as exc_info:
        registry_management_service.create_registry_entity_version_request(
            "postgresql://ignored",
            entity_type="agent",
            entity_id="agent.alpha",
            payload={"version": "v2", "spec": {}, "publish": False},
            current_user={"id": 10, "role": "user"},
        )

    assert exc_info.value.code == "insufficient_role"


def test_share_registry_model_request_shapes_share_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        registry_management_service,
        "get_entity",
        lambda *_args, **_kwargs: {"entity_id": "model.alpha", "owner_user_id": 10},
    )

    def _grant_share(
        _database_url: str,
        *,
        current_user: dict[str, object],
        entity: dict[str, object],
        grantee_type: str,
        grantee_id: str | None,
        permission: str,
    ) -> dict[str, object]:
        captured["current_user"] = current_user
        captured["entity"] = entity
        captured["grantee_type"] = grantee_type
        captured["grantee_id"] = grantee_id
        captured["permission"] = permission
        return {"entity_id": entity["entity_id"], "permission": permission}

    monkeypatch.setattr(registry_management_service, "grant_share", _grant_share)

    payload = registry_management_service.share_registry_model_request(
        "postgresql://ignored",
        entity_id="model.alpha",
        payload={"grantee_type": "public", "permission": "view"},
        current_user={"id": 10, "role": "superadmin"},
    )

    assert captured["grantee_type"] == "public"
    assert captured["grantee_id"] is None
    assert payload["permission"] == "view"
