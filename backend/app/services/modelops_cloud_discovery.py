from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import AuthConfig
from ..repositories import modelops as modelops_repo
from ..repositories.model_credentials import get_active_credential_secret
from .modelops_common import ModelOpsError
from .platform_adapters import http_json_request

_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible"}
_OPENAI_DEFAULT_API_BASE_URL = "https://api.openai.com/v1"


def discover_cloud_provider_models(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    provider: str,
    credential_id: str,
) -> dict[str, Any]:
    normalized_provider = str(provider or "").strip().lower()
    normalized_credential_id = str(credential_id or "").strip()
    if not normalized_provider:
        raise ModelOpsError("missing_config", "provider is required", status_code=400)
    if not normalized_credential_id:
        raise ModelOpsError("missing_config", "credential_id is required", status_code=400)
    if normalized_provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        raise ModelOpsError(
            "provider_discovery_unsupported",
            "Cloud model discovery is not supported for this provider yet",
            status_code=409,
            details={"provider": normalized_provider},
        )

    try:
        secret = get_active_credential_secret(
            database_url,
            credential_id=normalized_credential_id,
            requester_user_id=actor_user_id,
            requester_role=actor_role,
            encryption_key=config.model_credentials_encryption_key,
        )
    except ValueError as exc:
        raise ModelOpsError("invalid_credential_id", "credential_id must be a UUID", status_code=400) from exc
    if secret is None:
        raise ModelOpsError("missing_config", "Active credential not found", status_code=400)

    credential_provider = str(secret.get("provider_slug") or "").strip().lower()
    if credential_provider != normalized_provider:
        raise ModelOpsError(
            "credential_provider_mismatch",
            "Credential provider does not match the selected provider",
            status_code=400,
            details={"credential_provider": credential_provider, "provider": normalized_provider},
        )

    api_base_url = str(secret.get("api_base_url") or "").strip().rstrip("/")
    if not api_base_url and normalized_provider == "openai":
        api_base_url = _OPENAI_DEFAULT_API_BASE_URL
    if not api_base_url:
        raise ModelOpsError("missing_config", "Cloud credential is missing api_base_url", status_code=400)

    payload, status_code = http_json_request(
        f"{api_base_url}/models",
        method="GET",
        headers={"Authorization": f"Bearer {str(secret.get('api_key') or '').strip()}"},
        timeout_seconds=8.0,
    )
    if payload is None or status_code >= 400:
        raise ModelOpsError(
            "provider_model_discovery_failed",
            "Unable to discover provider models",
            status_code=502,
            details={"provider": normalized_provider, "status_code": status_code},
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ModelOpsError(
            "provider_model_discovery_failed",
            "Provider returned an invalid model list",
            status_code=502,
            details={"provider": normalized_provider, "status_code": status_code},
        )

    models = sorted(
        [
            _serialize_provider_model(item)
            for item in payload["data"]
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ],
        key=lambda item: item["provider_model_id"],
    )
    return {
        "provider": normalized_provider,
        "credential_id": normalized_credential_id,
        "models": models,
    }


def _serialize_provider_model(item: dict[str, Any]) -> dict[str, Any]:
    provider_model_id = str(item.get("id") or "").strip()
    task_key = _infer_task_key(provider_model_id)
    return {
        "provider_model_id": provider_model_id,
        "name": provider_model_id,
        "owned_by": str(item.get("owned_by") or "").strip() or None,
        "created_at": _serialize_created_at(item.get("created")),
        "task_key": task_key,
        "category": modelops_repo.infer_category(task_key),
        "metadata": {
            "provider_model_id": provider_model_id,
            "owned_by": str(item.get("owned_by") or "").strip() or None,
            "created": item.get("created"),
            "object": str(item.get("object") or "").strip() or None,
        },
    }


def _infer_task_key(provider_model_id: str) -> str:
    normalized = provider_model_id.strip().lower()
    if normalized.startswith("text-embedding") or "embedding" in normalized or "embed" in normalized:
        return modelops_repo.TASK_EMBEDDINGS
    return modelops_repo.TASK_LLM


def _serialize_created_at(value: Any) -> str | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
