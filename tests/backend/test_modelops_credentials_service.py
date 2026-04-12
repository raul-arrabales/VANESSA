from __future__ import annotations

import pytest

from app.application import modelops_credentials_service
from app.services.modelops_common import ModelOpsError


def test_build_create_credential_request_enforces_platform_scope_permissions() -> None:
    request = modelops_credentials_service.build_create_credential_request(
        {"provider": "openai_compatible", "api_key": "sk-test"},
        current_user_id=7,
        actor_role="user",
    )
    assert request["owner_user_id"] == 7
    assert request["credential_scope"] == "personal"

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_credentials_service.build_create_credential_request(
            {"credential_scope": "platform", "provider": "openai_compatible", "api_key": "sk-test"},
            current_user_id=7,
            actor_role="user",
        )

    assert exc_info.value.code == "forbidden"


def test_revoke_credential_marks_referencing_cloud_models_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    revoked = {"id": "00000000-0000-0000-0000-000000000001", "display_name": "old-key"}
    affected = [{"model_id": "gpt-private", "lifecycle_state": "inactive"}]

    monkeypatch.setattr(modelops_credentials_service, "_revoke_credential", lambda *args, **kwargs: revoked)
    monkeypatch.setattr(
        modelops_credentials_service.modelops_repo,
        "mark_models_for_revoked_credential",
        lambda *args, **kwargs: affected,
    )

    result = modelops_credentials_service.revoke_credential(
        "postgresql://ignored",
        credential_id="00000000-0000-0000-0000-000000000001",
        owner_user_id=7,
    )

    assert result == {"credential": revoked, "affected_models": affected}


def test_create_credential_maps_duplicate_name_to_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_duplicate(*args, **kwargs):
        raise ValueError("duplicate_credential")

    monkeypatch.setattr(modelops_credentials_service, "_create_credential", _raise_duplicate)

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_credentials_service.create_credential(
            "postgresql://ignored",
            owner_user_id=7,
            credential_scope="personal",
            provider_slug="openai",
            display_name="existing",
            api_base_url=None,
            api_key="sk-test",
            encryption_key="secret",
            created_by_user_id=7,
        )

    assert exc_info.value.code == "duplicate_credential"
    assert exc_info.value.status_code == 409
