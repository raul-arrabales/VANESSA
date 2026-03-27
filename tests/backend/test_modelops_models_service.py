from __future__ import annotations

import pytest

from app.application import modelops_models_service
from app.services.modelops_common import ModelOpsError


def test_parse_limit_clamps_and_rejects_invalid_values() -> None:
    assert modelops_models_service.parse_limit("200", default=20, minimum=1, maximum=100) == 100
    assert modelops_models_service.parse_limit("0", default=20, minimum=1, maximum=100) == 1

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_models_service.parse_limit("nope", default=20, minimum=1, maximum=100)

    assert exc_info.value.code == "invalid_limit"


def test_create_model_requires_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        modelops_models_service,
        "_create_model",
        lambda database_url, *, config, actor_user_id, actor_role, payload: {
            "database_url": database_url,
            "payload": payload,
        },
    )

    payload = {"id": "model-1", "name": "Model", "provider": "local", "backend": "local", "task_key": "llm"}
    result = modelops_models_service.create_model(
        "postgresql://example",
        config=object(),
        actor_user_id=1,
        actor_role="superadmin",
        payload=payload,
    )
    assert result["payload"] == payload

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_models_service.create_model(
            "postgresql://example",
            config=object(),
            actor_user_id=1,
            actor_role="superadmin",
            payload=[],
        )
    assert exc_info.value.code == "invalid_payload"
