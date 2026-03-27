from __future__ import annotations

import pytest

from app.application import platform_control_service


def test_create_platform_provider_requires_json_object() -> None:
    with pytest.raises(platform_control_service.PlatformControlRequestError) as exc_info:
        platform_control_service.create_platform_provider(
            "postgresql://ignored",
            config=object(),
            payload=[],
        )

    assert exc_info.value.code == "invalid_payload"


def test_assign_platform_provider_loaded_model_extracts_managed_model_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _assign_provider_loaded_model(_database_url: str, *, config, provider_instance_id: str, managed_model_id: str):
        captured["config"] = config
        captured["provider_instance_id"] = provider_instance_id
        captured["managed_model_id"] = managed_model_id
        return {"id": provider_instance_id, "loaded_managed_model_id": managed_model_id}

    monkeypatch.setattr(platform_control_service, "_assign_provider_loaded_model", _assign_provider_loaded_model)

    payload = platform_control_service.assign_platform_provider_loaded_model(
        "postgresql://ignored",
        config="config",
        provider_instance_id="provider-1",
        payload={"managed_model_id": " model-1 "},
    )

    assert captured == {
        "config": "config",
        "provider_instance_id": "provider-1",
        "managed_model_id": "model-1",
    }
    assert payload["loaded_managed_model_id"] == "model-1"


def test_query_platform_vector_documents_requires_json_object() -> None:
    with pytest.raises(platform_control_service.PlatformControlRequestError) as exc_info:
        platform_control_service.query_platform_vector_documents(
            "postgresql://ignored",
            object(),
            None,
        )

    assert exc_info.value.code == "invalid_payload"
