from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..config import AuthConfig
from ..repositories.model_credentials import get_active_credential_secret_by_id
from .platform_types import PlatformControlPlaneError, ProviderBinding

MODEL_CREDENTIAL_SECRET_REF_PREFIX = "modelops://credential/"
_LEGACY_MODEL_CREDENTIAL_SECRET_REF_PREFIX = "modelops://"
_OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS = {
    "openai_compatible_cloud_llm",
    "openai_compatible_cloud_embeddings",
}
_OPENAI_COMPATIBLE_CREDENTIAL_PROVIDERS = {"openai", "openai_compatible"}
_OPENAI_DEFAULT_API_BASE_URL = "https://api.openai.com/v1"


def credential_id_from_secret_ref(reference: Any) -> str | None:
    normalized = str(reference or "").strip()
    if normalized.startswith(MODEL_CREDENTIAL_SECRET_REF_PREFIX):
        return normalized.removeprefix(MODEL_CREDENTIAL_SECRET_REF_PREFIX).strip() or None
    if normalized.startswith(_LEGACY_MODEL_CREDENTIAL_SECRET_REF_PREFIX):
        return normalized.removeprefix(_LEGACY_MODEL_CREDENTIAL_SECRET_REF_PREFIX).strip() or None
    return None


def model_credential_secret_ref(credential_id: str) -> str:
    return f"{MODEL_CREDENTIAL_SECRET_REF_PREFIX}{credential_id.strip()}"


def resolve_binding_modelops_credential(
    database_url: str,
    *,
    config: AuthConfig,
    binding: ProviderBinding,
) -> tuple[ProviderBinding, dict[str, Any] | None]:
    raw_secret_refs = binding.config.get("secret_refs")
    secret_refs = dict(raw_secret_refs) if isinstance(raw_secret_refs, dict) else {}
    credential_id = credential_id_from_secret_ref(secret_refs.get("api_key"))
    if not credential_id:
        return binding, None
    if binding.provider_key not in _OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS:
        raise PlatformControlPlaneError(
            "credential_ref_unsupported",
            "Saved credentials are only supported for OpenAI-compatible cloud providers",
            status_code=409,
            details={"provider_key": binding.provider_key},
        )
    try:
        secret = get_active_credential_secret_by_id(
            database_url,
            credential_id=credential_id,
            encryption_key=config.model_credentials_encryption_key,
        )
    except ValueError as exc:
        raise PlatformControlPlaneError("invalid_credential_id", "credential_id must be a UUID", status_code=400) from exc
    if secret is None:
        raise PlatformControlPlaneError(
            "credential_not_found",
            "Active credential not found",
            status_code=404,
            details={"credential_id": credential_id, "provider_key": binding.provider_key},
        )

    credential_provider = str(secret.get("provider_slug") or "").strip().lower()
    if credential_provider not in _OPENAI_COMPATIBLE_CREDENTIAL_PROVIDERS:
        raise PlatformControlPlaneError(
            "credential_provider_mismatch",
            "Credential provider does not match this platform provider",
            status_code=409,
            details={"credential_provider": credential_provider, "provider_key": binding.provider_key},
        )

    credential_base_url = str(secret.get("api_base_url") or "").strip()
    if not credential_base_url and credential_provider == "openai":
        credential_base_url = _OPENAI_DEFAULT_API_BASE_URL
    endpoint_url = credential_base_url or binding.endpoint_url
    if not endpoint_url:
        raise PlatformControlPlaneError(
            "missing_credential_api_base_url",
            "Credential is missing api_base_url and the provider has no endpoint URL",
            status_code=400,
        )

    next_config = dict(binding.config)
    raw_resolved_secret_refs = next_config.get("secret_refs")
    resolved_secret_refs = dict(raw_resolved_secret_refs) if isinstance(raw_resolved_secret_refs, dict) else {}
    resolved_secret_refs["api_key"] = str(secret.get("api_key") or "").strip()
    next_config["secret_refs"] = resolved_secret_refs
    next_config.setdefault("request_timeout_seconds", getattr(config, "llm_request_timeout_seconds", 60))
    if binding.provider_key == "openai_compatible_cloud_llm" and credential_provider == "openai":
        next_config.setdefault("models_path", "/models")
        next_config.setdefault("chat_completion_path", "/chat/completions")
        next_config.setdefault("request_format", "openai_chat")
    if binding.provider_key == "openai_compatible_cloud_embeddings" and credential_provider == "openai":
        next_config.setdefault("models_path", "/models")
        next_config.setdefault("embeddings_path", "/embeddings")
    summary = {
        "id": str(secret.get("id") or credential_id),
        "provider": credential_provider,
        "display_name": str(secret.get("display_name") or ""),
        "api_base_url": credential_base_url or None,
    }
    return replace(binding, endpoint_url=endpoint_url, healthcheck_url=None, config=next_config), summary
