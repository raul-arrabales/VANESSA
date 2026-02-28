from __future__ import annotations

from typing import Any

from ..repositories.model_management import get_model_by_id, list_models_visible_to_user
from .runtime_profile_service import resolve_runtime_profile


def list_models_for_user(database_url: str, *, user_id: int) -> tuple[str, list[dict[str, Any]]]:
    runtime_profile = resolve_runtime_profile(database_url)
    rows = list_models_visible_to_user(
        database_url,
        user_id=user_id,
        runtime_profile=runtime_profile,
    )
    return runtime_profile, rows


def resolve_model_for_inference(
    database_url: str,
    *,
    user_id: int,
    requested_model_id: str,
) -> tuple[str | None, dict[str, Any] | None, int]:
    runtime_profile, visible_models = list_models_for_user(database_url, user_id=user_id)
    visible_ids = {str(model.get("model_id", "")).strip() for model in visible_models}

    if requested_model_id in visible_ids:
        return requested_model_id, None, 200

    registered = get_model_by_id(database_url, requested_model_id)
    if (
        runtime_profile == "offline"
        and registered is not None
        and str(registered.get("backend_kind", "")).strip().lower() == "external_api"
    ):
        local_candidates = [
            str(model.get("model_id", "")).strip()
            for model in visible_models
            if str(model.get("backend_kind", "")).strip().lower() == "local"
            or str(model.get("availability", "")).strip().lower() == "offline_ready"
        ]
        local_candidates = [candidate for candidate in local_candidates if candidate]
        return (
            None,
            {
                "error": "model_unavailable_offline",
                "message": "Requested model is external API-backed and unavailable in offline mode",
                "action": "choose_local_model",
                "available_local_models": local_candidates,
            },
            409,
        )

    return (
        None,
        {"error": "model_forbidden", "message": "Requested model is not allowed"},
        403,
    )
