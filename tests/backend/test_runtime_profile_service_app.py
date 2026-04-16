from __future__ import annotations

import pytest

from app.application import runtime_profile_service_app


def test_update_runtime_profile_state_requires_json_object() -> None:
    with pytest.raises(runtime_profile_service_app.RuntimeProfileRequestError) as exc_info:
        runtime_profile_service_app.update_runtime_profile_state_response(
            "postgresql://ignored",
            payload=[],
            updated_by_user_id=1,
        )

    assert exc_info.value.code == "invalid_payload"


def test_update_runtime_profile_state_maps_locked_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime_profile_service_app,
        "_update_runtime_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime_profile_service_app.RuntimeProfileLockedError("offline")
        ),
    )

    with pytest.raises(runtime_profile_service_app.RuntimeProfileRequestError) as exc_info:
        runtime_profile_service_app.update_runtime_profile_state_response(
            "postgresql://ignored",
            payload={"profile": "online"},
            updated_by_user_id=7,
            update_runtime_profile_fn=runtime_profile_service_app._update_runtime_profile,
        )

    assert exc_info.value.code == "runtime_profile_locked"


def test_update_runtime_profile_state_rejects_offline_with_active_cloud_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime_profile_service_app.platform_repo,
        "get_active_deployment",
        lambda _db: {"deployment_profile_id": "deployment-cloud"},
    )
    monkeypatch.setattr(
        runtime_profile_service_app.platform_repo,
        "list_deployment_bindings",
        lambda _db, *, deployment_profile_id: [
            {
                "provider_instance_id": "provider-openai",
                "provider_key": "openai_compatible_cloud_llm",
                "provider_origin": "cloud",
            }
        ],
    )
    monkeypatch.setattr(
        runtime_profile_service_app,
        "_update_runtime_profile",
        lambda *_args, **_kwargs: pytest.fail("runtime profile should not switch offline with an active cloud provider"),
    )

    with pytest.raises(runtime_profile_service_app.RuntimeProfileRequestError) as exc_info:
        runtime_profile_service_app.update_runtime_profile_state_response(
            "postgresql://ignored",
            payload={"profile": "offline"},
            updated_by_user_id=7,
            update_runtime_profile_fn=runtime_profile_service_app._update_runtime_profile,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "offline_provider_blocked"
    assert exc_info.value.details == {
        "runtime_profile": "offline",
        "provider_origin": "cloud",
        "provider_key": "openai_compatible_cloud_llm",
        "provider_instance_id": "provider-openai",
    }


def test_get_runtime_profile_state_serializes_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime_profile_service_app,
        "_resolve_runtime_profile_state",
        lambda _database_url: runtime_profile_service_app.RuntimeProfileState(
            profile="offline",
            locked=False,
            source="database",
        ),
    )

    payload = runtime_profile_service_app.get_runtime_profile_state_response(
        "postgresql://ignored",
        resolve_runtime_profile_state_fn=runtime_profile_service_app._resolve_runtime_profile_state,
    )

    assert payload == {
        "profile": "offline",
        "locked": False,
        "source": "database",
    }
