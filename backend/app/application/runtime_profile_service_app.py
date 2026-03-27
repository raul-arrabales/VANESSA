from __future__ import annotations

from typing import Any, Callable

from ..services.runtime_profile_service import (
    RuntimeProfileLockedError,
    RuntimeProfileState,
    resolve_runtime_profile_state as _resolve_runtime_profile_state,
    update_runtime_profile as _update_runtime_profile,
)


class RuntimeProfileRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def serialize_runtime_profile_state(state: RuntimeProfileState) -> dict[str, object]:
    return {
        "profile": state.profile,
        "locked": state.locked,
        "source": state.source,
    }


def get_runtime_profile_state_response(
    database_url: str,
    *,
    resolve_runtime_profile_state_fn: Callable[[str], RuntimeProfileState] = _resolve_runtime_profile_state,
) -> dict[str, object]:
    return serialize_runtime_profile_state(resolve_runtime_profile_state_fn(database_url))


def update_runtime_profile_state_response(
    database_url: str,
    *,
    payload: Any,
    updated_by_user_id: int,
    update_runtime_profile_fn: Callable[..., str] = _update_runtime_profile,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeProfileRequestError(status_code=400, code="invalid_payload", message="Expected JSON object")

    profile = str(payload.get("profile", "")).strip().lower()
    if not profile:
        raise RuntimeProfileRequestError(status_code=400, code="invalid_profile", message="profile is required")

    try:
        updated = update_runtime_profile_fn(
            database_url,
            profile=profile,
            updated_by_user_id=updated_by_user_id,
        )
    except RuntimeProfileLockedError as exc:
        raise RuntimeProfileRequestError(
            status_code=409,
            code="runtime_profile_locked",
            message=str(exc),
        ) from exc
    except ValueError as exc:
        raise RuntimeProfileRequestError(
            status_code=400,
            code="invalid_profile",
            message=str(exc),
        ) from exc

    return {"profile": updated, "locked": False, "source": "database"}
