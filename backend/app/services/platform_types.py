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
    resource_policy: dict[str, Any] = field(default_factory=dict)
    resources: list[dict[str, Any]] = field(default_factory=list)
    default_resource_id: str | None = None
    default_resource: dict[str, Any] | None = None
    provider_origin: str = "local"

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProviderBinding":
        resources = _resources_from_row(row)
        default_resource_id = str(row.get("default_resource_id", "")).strip() or None
        default_resource = (
            dict(row.get("default_resource"))
            if isinstance(row.get("default_resource"), dict)
            else next((dict(resource) for resource in resources if str(resource.get("id", "")).strip() == default_resource_id), None)
        )
        return cls(
            capability_key=str(row.get("capability_key", "")).strip().lower(),
            provider_instance_id=str(row.get("provider_instance_id") or row.get("id") or "").strip(),
            provider_slug=str(row.get("provider_slug") or row.get("slug") or "").strip(),
            provider_key=str(row.get("provider_key", "")).strip().lower(),
            provider_origin=str(row.get("provider_origin") or "local").strip().lower(),
            provider_display_name=str(
                row.get("provider_display_name")
                or row.get("display_name")
                or row.get("provider_slug")
                or row.get("slug")
                or ""
            ).strip(),
            provider_description=str(row.get("provider_description") or row.get("description") or "").strip(),
            endpoint_url=_optional_text(row.get("endpoint_url")) or "",
            healthcheck_url=_optional_text(row.get("healthcheck_url")),
            enabled=bool(row.get("enabled", True)),
            adapter_kind=str(row.get("adapter_kind", "")).strip().lower(),
            config=dict(row.get("config_json") or row.get("config") or {}),
            resources=resources,
            default_resource_id=default_resource_id,
            default_resource=default_resource,
            binding_config=dict(row.get("binding_config") or {}),
            resource_policy=dict(row.get("resource_policy") or {}),
            deployment_profile_id=str(row.get("deployment_profile_id", "")).strip(),
            deployment_profile_slug=str(row.get("deployment_profile_slug", "")).strip(),
            deployment_profile_display_name=str(row.get("deployment_profile_display_name", "")).strip(),
        )


def _optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized or normalized.lower() in {"none", "null"}:
        return None
    return normalized


@dataclass(frozen=True)
class DeploymentBindingInput:
    capability_key: str
    provider_instance_id: str
    resources: list[dict[str, Any]] = field(default_factory=list)
    default_resource_id: str | None = None
    binding_config: dict[str, Any] = field(default_factory=dict)
    resource_policy: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeploymentProfileCreateInput:
    slug: str
    display_name: str
    description: str
    bindings: list[DeploymentBindingInput]


def _resources_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw_resources = row.get("resources")
    if isinstance(raw_resources, list):
        normalized: list[dict[str, Any]] = []
        for item in raw_resources:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return normalized
    return []
