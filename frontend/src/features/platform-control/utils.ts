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
  servedModelIdsByCapability: Record<string, string[]>;
  defaultServedModelIdsByCapability: Record<string, string>;
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
  servedModelIdsByCapability: {},
  defaultServedModelIdsByCapability: {},
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

export function capabilityRequiresServedModel(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
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
    servedModelIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, (binding.served_models ?? []).map((model) => model.id)]),
    ),
    defaultServedModelIdsByCapability: Object.fromEntries(
      deployment.bindings.map((binding) => [binding.capability, binding.default_served_model_id ?? ""]),
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

export function summarizeServedModels(
  servedModels: Array<{ id: string; name?: string | null }> | undefined,
  defaultServedModel: { id: string; name?: string | null } | null | undefined,
  noneLabel: string,
): string {
  const models = servedModels ?? [];
  if (!defaultServedModel && models.length === 0) {
    return noneLabel;
  }

  const primary = defaultServedModel ?? models[0];
  if (!primary) {
    return noneLabel;
  }

  const primaryLabel = getModelDisplayName(primary);
  const additionalCount = Math.max(models.length - 1, 0);
  if (additionalCount === 0) {
    return primaryLabel;
  }
  return `${primaryLabel} (+${additionalCount})`;
}

export function summarizeBindingServedModels(binding: PlatformDeploymentBinding, noneLabel: string): string {
  return summarizeServedModels(binding.served_models, binding.default_served_model, noneLabel);
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

export function getServedModelsByCapability(
  eligibleModelsByCapability: Record<string, ManagedModel[]>,
  capabilities: PlatformCapability[],
): Record<string, ManagedModel[]> {
  return capabilities.reduce<Record<string, ManagedModel[]>>((accumulator, capability) => {
    accumulator[capability.capability] = capabilityRequiresServedModel(capability.capability)
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
    servedModelRequiredMessage: (capabilityDisplayName: string) => string;
    defaultServedModelRequiredMessage: (capabilityDisplayName: string) => string;
  },
): string | null {
  const missingBinding = requiredCapabilities.find((capability) => !form.providerIdsByCapability[capability.capability]);
  if (missingBinding) {
    return options.bindingRequiredMessage;
  }

  const missingServedModel = requiredCapabilities.find(
    (capability) =>
      capabilityRequiresServedModel(capability.capability) &&
      (form.servedModelIdsByCapability[capability.capability]?.length ?? 0) === 0,
  );
  if (missingServedModel) {
    return options.servedModelRequiredMessage(missingServedModel.display_name);
  }

  const missingDefaultServedModel = requiredCapabilities.find(
    (capability) =>
      capabilityRequiresServedModel(capability.capability) &&
      (form.servedModelIdsByCapability[capability.capability]?.length ?? 0) > 0 &&
      !form.defaultServedModelIdsByCapability[capability.capability],
  );
  if (missingDefaultServedModel) {
    return options.defaultServedModelRequiredMessage(missingDefaultServedModel.display_name);
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
      served_model_ids: capabilityRequiresServedModel(capability.capability)
        ? form.servedModelIdsByCapability[capability.capability] ?? []
        : [],
      default_served_model_id: capabilityRequiresServedModel(capability.capability)
        ? form.defaultServedModelIdsByCapability[capability.capability] || null
        : null,
      config: {},
    })),
  };
}
