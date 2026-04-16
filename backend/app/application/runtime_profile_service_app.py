from __future__ import annotations

from typing import Any, Callable

from ..repositories import platform_control_plane as platform_repo
from ..services.platform_types import PlatformControlPlaneError
from ..services.provider_origin_policy import assert_bindings_allowed_for_runtime_profile
from ..services.runtime_profile_service import (
    RuntimeProfileLockedError,
    RuntimeProfileState,
    resolve_runtime_profile_state as _resolve_runtime_profile_state,
    update_runtime_profile as _update_runtime_profile,
)


class RuntimeProfileRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


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
    if profile == "offline":
        active_deployment = platform_repo.get_active_deployment(database_url)
        if active_deployment is not None:
            bindings = platform_repo.list_deployment_bindings(
                database_url,
                deployment_profile_id=str(active_deployment["deployment_profile_id"]),
            )
            try:
                assert_bindings_allowed_for_runtime_profile(runtime_profile=profile, bindings=bindings)
            except PlatformControlPlaneError as exc:
                raise RuntimeProfileRequestError(
                    status_code=exc.status_code,
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                ) from exc

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
