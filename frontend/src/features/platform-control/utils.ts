import type { ManagedModel } from "../../api/modelops";
import type {
  PlatformCapability,
  PlatformDeploymentBinding,
  PlatformDeploymentMutationInput,
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

export type DeploymentFormState = {
  slug: string;
  displayName: string;
  description: string;
  providerIdsByCapability: Record<string, string>;
  resourceIdsByCapability: Record<string, string[]>;
  defaultResourceIdsByCapability: Record<string, string>;
  resourcePolicyByCapability: Record<string, Record<string, unknown>>;
};

export type DeploymentCloneFormState = {
  slug: string;
  displayName: string;
  description: string;
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

export const DEFAULT_DEPLOYMENT_FORM: DeploymentFormState = {
  slug: "",
  displayName: "",
  description: "",
  providerIdsByCapability: {},
  resourceIdsByCapability: {},
  defaultResourceIdsByCapability: {},
  resourcePolicyByCapability: {},
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

export function buildDeploymentForm(deployment: PlatformDeploymentProfile): DeploymentFormState {
  return {
    slug: deployment.slug,
    displayName: deployment.display_name,
    description: deployment.description,
    providerIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.provider.id]),
    ),
    resourceIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, (binding.resources ?? []).map((resource) => resource.id)]),
    ),
    defaultResourceIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.default_resource_id ?? ""]),
    ),
    resourcePolicyByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.resource_policy ?? {}]),
    ),
  };
}

export function buildCloneForm(deployment: PlatformDeploymentProfile): DeploymentCloneFormState {
  return {
    slug: `${deployment.slug}-copy`,
    displayName: `${deployment.display_name} Copy`,
    description: deployment.description,
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

export function getCapabilityProviders(
  providers: PlatformProvider[],
  capabilities: PlatformCapability[],
): Record<string, PlatformProvider[]> {
  return capabilities.reduce<Record<string, PlatformProvider[]>>((accumulator, capability) => {
    accumulator[capability.capability] = providers.filter((provider) => provider.capability === capability.capability);
    return accumulator;
  }, {});
}

export function getManagedModelsByCapability(
  eligibleModelsByCapability: Record<string, ManagedModel[]>,
  capabilities: PlatformCapability[],
): Record<string, ManagedModel[]> {
  return capabilities.reduce<Record<string, ManagedModel[]>>((accumulator, capability) => {
    accumulator[capability.capability] = capabilityRequiresModelResource(capability.capability)
      ? eligibleModelsByCapability[capability.capability] ?? []
      : [];
    return accumulator;
  }, {});
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

export function validateDeploymentForm(
  requiredCapabilities: PlatformCapability[],
  form: DeploymentFormState,
  options: {
    bindingRequiredMessage: string;
    resourceRequiredMessage: (capabilityDisplayName: string) => string;
    defaultResourceRequiredMessage: (capabilityDisplayName: string) => string;
  },
): string | null {
  const missingBinding = requiredCapabilities.find((capability) => !form.providerIdsByCapability[capability.capability]);
  if (missingBinding) {
    return options.bindingRequiredMessage;
  }

  const missingServedModel = requiredCapabilities.find(
    (capability) =>
      capabilityRequiresModelResource(capability.capability) &&
      (form.resourceIdsByCapability[capability.capability]?.length ?? 0) === 0,
  );
  if (missingServedModel) {
    return options.resourceRequiredMessage(missingServedModel.display_name);
  }

  const missingDefaultServedModel = requiredCapabilities.find(
    (capability) =>
      capabilityRequiresModelResource(capability.capability) &&
      (form.resourceIdsByCapability[capability.capability]?.length ?? 0) > 0 &&
      !form.defaultResourceIdsByCapability[capability.capability],
  );
  if (missingDefaultServedModel) {
    return options.defaultResourceRequiredMessage(missingDefaultServedModel.display_name);
  }

  const invalidVectorBinding = requiredCapabilities.find((capability) => {
    if (capability.capability !== "vector_store") {
      return false;
    }
    const policy = form.resourcePolicyByCapability[capability.capability] ?? {};
    const selectionMode = String(policy.selection_mode ?? "explicit");
    if (selectionMode === "dynamic_namespace") {
      return !String(policy.namespace_prefix ?? "").trim();
    }
    return (form.resourceIdsByCapability[capability.capability]?.length ?? 0) === 0;
  });
  if (invalidVectorBinding) {
    return options.resourceRequiredMessage(invalidVectorBinding.display_name);
  }

  return null;
}

export function buildDeploymentMutationInput(
  requiredCapabilities: PlatformCapability[],
  form: DeploymentFormState,
): PlatformDeploymentMutationInput {
  return {
    slug: form.slug,
    display_name: form.displayName,
    description: form.description,
    bindings: requiredCapabilities.map((capability) => ({
      capability: capability.capability,
      provider_id: form.providerIdsByCapability[capability.capability],
      resources: capability.capability === "vector_store"
        ? (form.resourceIdsByCapability[capability.capability] ?? []).map((resourceId) => ({
            id: resourceId,
            resource_kind: "index",
            ref_type: "provider_resource",
            provider_resource_id: resourceId,
            display_name: resourceId,
            metadata: {},
          }))
        : (form.resourceIdsByCapability[capability.capability] ?? []).map((resourceId) => ({
            id: resourceId,
            resource_kind: "model",
            ref_type: "managed_model",
            managed_model_id: resourceId,
            display_name: resourceId,
            metadata: {},
          })),
      default_resource_id: capabilitySupportsResources(capability.capability)
        ? form.defaultResourceIdsByCapability[capability.capability] || null
        : null,
      resource_policy: capability.capability === "vector_store"
        ? {
            selection_mode:
              String(form.resourcePolicyByCapability[capability.capability]?.selection_mode ?? "explicit"),
            ...(form.resourcePolicyByCapability[capability.capability] ?? {}),
          }
        : (capabilitySupportsResources(capability.capability)
            ? form.resourcePolicyByCapability[capability.capability] ?? {}
            : {}),
      config: {},
    })),
  };
}
