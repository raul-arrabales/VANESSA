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
