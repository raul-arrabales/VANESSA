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
