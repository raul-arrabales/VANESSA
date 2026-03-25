import type { ManagedModel } from "../../api/modelops";
import type {
  PlatformCapability,
  PlatformDeploymentMutationInput,
  PlatformDeploymentProfile,
  PlatformProvider,
} from "../../api/platform";
import {
  capabilityRequiresModelResource,
  capabilitySupportsResources,
} from "./utils";

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

export const DEFAULT_DEPLOYMENT_FORM: DeploymentFormState = {
  slug: "",
  displayName: "",
  description: "",
  providerIdsByCapability: {},
  resourceIdsByCapability: {},
  defaultResourceIdsByCapability: {},
  resourcePolicyByCapability: {},
};

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
