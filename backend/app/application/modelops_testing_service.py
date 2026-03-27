from __future__ import annotations

from typing import Any

from ..services.modelops_common import ModelOpsError
from ..services.modelops_testing import (
    get_model_test_runtimes as _get_model_test_runtimes,
    get_model_tests as _get_model_tests,
    run_model_test as _run_model_test,
    validate_model as _validate_model,
)


def parse_test_limit(value: Any) -> int:
    raw_value = str(value if value is not None else 10).strip() or "10"
    try:
        return max(1, min(50, int(raw_value)))
    except ValueError as exc:
        raise ModelOpsError("invalid_limit", "limit must be an integer", status_code=400) from exc


def require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelOpsError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def parse_validation_request(payload: Any) -> str | None:
    body = {} if payload is None else require_json_object(payload)
    return str(body.get("test_run_id", "")).strip() or None


def parse_model_test_request(payload: Any) -> tuple[dict[str, Any], str | None]:
    body = require_json_object(payload)
    raw_inputs = body.get("inputs")
    if not isinstance(raw_inputs, dict):
        raise ModelOpsError("invalid_payload", "inputs must be an object", status_code=400)
    provider_instance_id = str(body.get("provider_instance_id", "")).strip() or None
    return raw_inputs, provider_instance_id


def get_model_tests(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    limit: int = 10,
):
    return _get_model_tests(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        limit=limit,
    )


def get_model_test_runtimes(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
):
    return _get_model_test_runtimes(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
    )


def run_model_test(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    inputs: dict[str, Any],
    provider_instance_id: str | None = None,
):
    return _run_model_test(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        inputs=inputs,
        provider_instance_id=provider_instance_id,
    )


def validate_model(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    model_id: str,
    trigger_reason: str,
    test_run_id: str | None = None,
):
    return _validate_model(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        model_id=model_id,
        trigger_reason=trigger_reason,
        test_run_id=test_run_id,
    )
