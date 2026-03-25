import type {
  PlatformDeploymentBinding,
  PlatformDeploymentProfile,
  PlatformProvider,
} from "../../api/platform";

export type LoadState = "idle" | "loading" | "success" | "error";

export type ProviderFormState = {
  providerKey: string;
  slug: string;
  displayName: string;
  description: string;
  endpointUrl: string;
  healthcheckUrl: string;
  enabled: boolean;
  configText: string;
  secretRefsText: string;
};

export const DEFAULT_PROVIDER_FORM: ProviderFormState = {
  providerKey: "",
  slug: "",
  displayName: "",
  description: "",
  endpointUrl: "",
  healthcheckUrl: "",
  enabled: true,
  configText: "{}",
  secretRefsText: "{}",
};

export function stringifyJson(value: Record<string, unknown> | Record<string, string>): string {
  return JSON.stringify(value, null, 2);
}

export function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

export function capabilityRequiresModelResource(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
}

export function getDeploymentCapabilityMode(capability: string): "model" | "vector" | "none" {
  if (capabilityRequiresModelResource(capability)) {
    return "model";
  }
  if (capability === "vector_store") {
    return "vector";
  }
  return "none";
}

export function capabilitySupportsResources(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings" || capability === "vector_store";
}

export function buildProviderForm(provider: PlatformProvider): ProviderFormState {
  return {
    providerKey: provider.provider_key,
    slug: provider.slug,
    displayName: provider.display_name,
    description: provider.description,
    endpointUrl: provider.endpoint_url,
    healthcheckUrl: provider.healthcheck_url ?? "",
    enabled: provider.enabled,
    configText: stringifyJson(provider.config),
    secretRefsText: stringifyJson(provider.secret_refs),
  };
}

export function getModelDisplayName(model: { id: string; name?: string | null }): string {
  return model.name?.trim() || model.id;
}

export function summarizeResources(
  resources: Array<{ id: string; display_name?: string | null; metadata?: Record<string, unknown> }> | undefined,
  defaultResource: { id: string; display_name?: string | null; metadata?: Record<string, unknown> } | null | undefined,
  noneLabel: string,
): string {
  const items = resources ?? [];
  if (!defaultResource && items.length === 0) {
    return noneLabel;
  }

  const primary = defaultResource ?? items[0];
  if (!primary) {
    return noneLabel;
  }

  const primaryLabel = primary.display_name?.trim() || String(primary.metadata?.name ?? primary.id);
  const additionalCount = Math.max(items.length - 1, 0);
  if (additionalCount === 0) {
    return primaryLabel;
  }
  return `${primaryLabel} (+${additionalCount})`;
}

export function summarizeBindingResources(binding: PlatformDeploymentBinding, noneLabel: string): string {
  return summarizeResources(binding.resources, binding.default_resource, noneLabel);
}

export function getActiveDeployment(
  deployments: PlatformDeploymentProfile[],
): PlatformDeploymentProfile | null {
  return deployments.find((deployment) => deployment.is_active) ?? null;
}

export function getProviderUsageEntries(
  providerId: string,
  deployments: PlatformDeploymentProfile[],
): Array<{
  deployment: PlatformDeploymentProfile;
  bindings: PlatformDeploymentBinding[];
}> {
  return deployments
    .map((deployment) => ({
      deployment,
      bindings: deployment.bindings.filter((binding) => binding.provider.id === providerId),
    }))
    .filter((entry) => entry.bindings.length > 0);
}
