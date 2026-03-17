from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CAPABILITY_LLM_INFERENCE = "llm_inference"
CAPABILITY_VECTOR_STORE = "vector_store"
REQUIRED_CAPABILITIES = {CAPABILITY_LLM_INFERENCE, CAPABILITY_VECTOR_STORE}


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

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProviderBinding":
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
            binding_config=dict(row.get("binding_config") or {}),
            deployment_profile_id=str(row.get("deployment_profile_id", "")).strip(),
            deployment_profile_slug=str(row.get("deployment_profile_slug", "")).strip(),
            deployment_profile_display_name=str(row.get("deployment_profile_display_name", "")).strip(),
        )


@dataclass(frozen=True)
class DeploymentBindingInput:
    capability_key: str
    provider_instance_id: str
    binding_config: dict[str, Any]


@dataclass(frozen=True)
class DeploymentProfileCreateInput:
    slug: str
    display_name: str
    description: str
    bindings: list[DeploymentBindingInput]
