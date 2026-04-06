from __future__ import annotations

from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from .modelops_policy import can_manage_model, get_accessible_model
from .modelops_serializers import (
    serialize_model,
    serialize_model_test_run,
    serialize_model_usage_summary,
    serialize_model_validation,
)
from .runtime_profile_service import resolve_runtime_profile


def list_models(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    require_active: bool = False,
    capability_key: str | None = None,
) -> list[dict[str, Any]]:
    _ = config
    runtime_profile = resolve_runtime_profile(database_url)
    rows = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=require_active,
        capability_key=capability_key,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        payload = serialize_model(row)
        payload["usage_summary"] = serialize_model_usage_summary(
            modelops_repo.get_usage_summary(database_url, model_id=str(row["model_id"])),
        )
        items.append(payload)
    return items


def list_model_picker_options(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    require_active: bool = False,
    capability_key: str | None = None,
) -> list[dict[str, Any]]:
    _ = config
    runtime_profile = resolve_runtime_profile(database_url)
    rows = modelops_repo.list_model_picker_rows_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=require_active,
        capability_key=capability_key,
    )
    return [
        {
            "id": str(row.get("model_id", "")),
            "display_name": str(row.get("name", "") or row.get("model_id", "")),
            "task_key": str(row.get("task_key", "")),
        }
        for row in rows
    ]


def get_model_detail(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    runtime_profile = resolve_runtime_profile(database_url)
    rows = modelops_repo.list_models_for_actor(
        database_url,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        runtime_profile=runtime_profile,
        require_active=False,
    )
    row = next((item for item in rows if str(item.get("model_id")) == model_id.strip()), None)
    if row is None:
        if actor_role == "superadmin":
            row = modelops_repo.get_model(database_url, model_id.strip())
        if row is None:
            from .modelops_common import ModelOpsError

            raise ModelOpsError("not_found", "Model not found", status_code=404)
    payload = serialize_model(row)
    payload["validation_history"] = [
        serialize_model_validation(item)
        for item in modelops_repo.list_validation_history(database_url, model_id=model_id)
    ]
    payload["usage_summary"] = serialize_model_usage_summary(
        modelops_repo.get_usage_summary(database_url, model_id=model_id),
    )
    return payload


def get_model_usage(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
) -> dict[str, Any]:
    get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    return {
        "model_id": model_id,
        "usage": serialize_model_usage_summary(modelops_repo.get_usage_summary(database_url, model_id=model_id)),
    }


def get_model_validations(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    return {
        "model_id": model_id,
        "validations": [
            serialize_model_validation(item)
            for item in modelops_repo.list_validation_history(database_url, model_id=model_id, limit=limit)
        ],
    }


def get_model_tests(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    row = get_accessible_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )
    can_manage_model(row, actor_user_id=actor_user_id, actor_role=actor_role, action="validate")
    tests = modelops_repo.list_model_test_runs(database_url, model_id=model_id, limit=limit)
    return {
        "model_id": model_id,
        "tests": [serialize_model_test_run(item) for item in tests],
    }
