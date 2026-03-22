from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from .modelops_common import ModelOpsError
from .modelops_queries import get_model_detail
from .runtime_profile_service import resolve_runtime_profile


logger = logging.getLogger(__name__)


def ensure_model_invokable(
    database_url: str,
    *,
    config: AuthConfig,
    user_id: int,
    user_role: str,
    model_id: str,
) -> dict[str, Any]:
    row = get_model_detail(
        database_url,
        config=config,
        actor_user_id=user_id,
        actor_role=user_role,
        model_id=model_id,
    )
    if row["lifecycle_state"] != "active":
        raise ModelOpsError("invalid_state_transition", "Model is not active", status_code=409)
    if not row["is_validation_current"] or row["last_validation_status"] != "success":
        raise ModelOpsError("validation_failed", "Model validation is not current", status_code=409)
    runtime_profile = resolve_runtime_profile(database_url)
    if runtime_profile != "online" and row["runtime_mode_policy"] == "online_only":
        raise ModelOpsError("offline_not_allowed", "Model is not available in offline mode", status_code=409)
    return row


def record_usage(
    database_url: str,
    *,
    model_id: str,
    user_id: int | None,
    usage_payload: dict[str, Any] | None,
    latency_ms: float,
) -> None:
    try:
        modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="calls", metric_value=1, request_count=1)
        modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="latency_ms", metric_value=latency_ms, request_count=0)
        usage_payload = usage_payload or {}
        prompt_tokens = usage_payload.get("prompt_tokens")
        completion_tokens = usage_payload.get("completion_tokens")
        if isinstance(prompt_tokens, (int, float)):
            modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="prompt_tokens", metric_value=float(prompt_tokens), request_count=0)
        if isinstance(completion_tokens, (int, float)):
            modelops_repo.record_daily_usage(database_url, model_id=model_id, user_id=user_id, metric_key="completion_tokens", metric_value=float(completion_tokens), request_count=0)
    except Exception:
        logger.exception("Failed to record ModelOps usage for model %s", model_id)


def measure_and_record_inference(
    database_url: str,
    *,
    model_id: str,
    user_id: int | None,
    callable_fn,
):
    started_at = perf_counter()
    payload, status_code = callable_fn()
    latency_ms = (perf_counter() - started_at) * 1000
    if status_code < 400 and isinstance(payload, dict):
        record_usage(
            database_url,
            model_id=model_id,
            user_id=user_id,
            usage_payload=payload.get("usage") if isinstance(payload.get("usage"), dict) else None,
            latency_ms=latency_ms,
        )
    return payload, status_code
