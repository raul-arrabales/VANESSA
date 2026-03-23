from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CAPABILITY_LLM_INFERENCE = "llm_inference"
CAPABILITY_EMBEDDINGS = "embeddings"
CAPABILITY_VECTOR_STORE = "vector_store"
CAPABILITY_MCP_RUNTIME = "mcp_runtime"
CAPABILITY_SANDBOX_EXECUTION = "sandbox_execution"
REQUIRED_CAPABILITIES = {CAPABILITY_LLM_INFERENCE, CAPABILITY_EMBEDDINGS, CAPABILITY_VECTOR_STORE}
OPTIONAL_CAPABILITIES = {CAPABILITY_MCP_RUNTIME, CAPABILITY_SANDBOX_EXECUTION}
ALL_CAPABILITIES = REQUIRED_CAPABILITIES | OPTIONAL_CAPABILITIES


class PlatformControlPlaneError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class ProviderBinding:
    capability_key: str
    provider_instance_id: str
    provider_slug: str
    provider_key: str
    provider_display_name: str
    provider_description: str
    endpoint_url: str
    healthcheck_url: str | None
    enabled: bool
    adapter_kind: str
    config: dict[str, Any]
    binding_config: dict[str, Any]
    deployment_profile_id: str
    deployment_profile_slug: str
    deployment_profile_display_name: str
    served_models: list[dict[str, Any]] = field(default_factory=list)
    default_served_model_id: str | None = None
    default_served_model: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProviderBinding":
        served_models = _served_models_from_row(row)
        default_served_model_id = (
            str(row.get("default_served_model_id", "")).strip()
            or str(row.get("served_model_id", "")).strip()
            or None
        )
        default_served_model = (
            dict(row.get("default_served_model"))
            if isinstance(row.get("default_served_model"), dict)
            else next((dict(model) for model in served_models if str(model.get("id", "")).strip() == default_served_model_id), None)
        )
        return cls(
            capability_key=str(row.get("capability_key", "")).strip().lower(),
            provider_instance_id=str(row.get("provider_instance_id") or row.get("id") or "").strip(),
            provider_slug=str(row.get("provider_slug") or row.get("slug") or "").strip(),
            provider_key=str(row.get("provider_key", "")).strip().lower(),
            provider_display_name=str(
                row.get("provider_display_name")
                or row.get("display_name")
                or row.get("provider_slug")
                or row.get("slug")
                or ""
            ).strip(),
            provider_description=str(row.get("provider_description") or row.get("description") or "").strip(),
            endpoint_url=str(row.get("endpoint_url", "")).strip(),
            healthcheck_url=str(row.get("healthcheck_url", "")).strip() or None,
            enabled=bool(row.get("enabled", True)),
            adapter_kind=str(row.get("adapter_kind", "")).strip().lower(),
            config=dict(row.get("config_json") or row.get("config") or {}),
            served_models=served_models,
            default_served_model_id=default_served_model_id,
            default_served_model=default_served_model,
            binding_config=dict(row.get("binding_config") or {}),
            deployment_profile_id=str(row.get("deployment_profile_id", "")).strip(),
            deployment_profile_slug=str(row.get("deployment_profile_slug", "")).strip(),
            deployment_profile_display_name=str(row.get("deployment_profile_display_name", "")).strip(),
        )


@dataclass(frozen=True)
class DeploymentBindingInput:
    capability_key: str
    provider_instance_id: str
    served_model_ids: list[str]
    default_served_model_id: str | None
    binding_config: dict[str, Any]


@dataclass(frozen=True)
class DeploymentProfileCreateInput:
    slug: str
    display_name: str
    description: str
    bindings: list[DeploymentBindingInput]


def _served_models_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw_models = row.get("served_models")
    if isinstance(raw_models, list):
        normalized: list[dict[str, Any]] = []
        for item in raw_models:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return normalized
    legacy_model_id = str(row.get("served_model_id", "")).strip()
    if legacy_model_id:
        return [
            {
                "id": legacy_model_id,
                "name": row.get("served_model_name"),
                "provider": row.get("served_model_provider"),
                "backend": row.get("served_model_backend_kind"),
                "task_key": row.get("served_model_task_key"),
                "provider_model_id": row.get("served_model_provider_model_id"),
                "local_path": row.get("served_model_local_path"),
                "source_id": row.get("served_model_source_id"),
                "availability": row.get("served_model_availability"),
            }
        ]
    return []
