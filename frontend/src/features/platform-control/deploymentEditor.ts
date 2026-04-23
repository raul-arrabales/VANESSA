import type { KnowledgeBase } from "../../api/context";
import type { ManagedModel } from "../../api/modelops";
import type {
  PlatformCapability,
  PlatformDeploymentBindingMutationInput,
  PlatformDeploymentIdentityMutationInput,
  PlatformDeploymentMutationInput,
  PlatformDeploymentProfile,
  PlatformProvider,
} from "../../api/platform";
import { capabilityRequiresModelResource, capabilitySupportsResources } from "./capabilities";
import { filterModelsForProviderOrigin } from "./deploymentModelCompatibility";

export type DeploymentFormState = {
  slug: string;
  displayName: string;
  description: string;
  capabilityKeys: string[];
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
  capabilityKeys: [],
  providerIdsByCapability: {},
  resourceIdsByCapability: {},
  defaultResourceIdsByCapability: {},
  resourcePolicyByCapability: {},
};

type DeploymentFormValidationOptions = {
  bindingRequiredMessage: string;
  resourceRequiredMessage?: (capability: PlatformCapability) => string;
  defaultResourceRequiredMessage?: (capability: PlatformCapability) => string;
  resourceCompatibilityMessage?: (
    capability: PlatformCapability,
    provider: PlatformProvider,
    resourceNames: string[],
  ) => string;
  providersByCapability?: Record<string, PlatformProvider[]>;
  modelResourcesByCapability?: Record<string, ManagedModel[]>;
};

function uniqueCapabilityKeys(capabilityKeys: string[]): string[] {
  return Array.from(new Set(capabilityKeys));
}

export function createDefaultDeploymentForm(requiredCapabilities: PlatformCapability[]): DeploymentFormState {
  return {
    ...DEFAULT_DEPLOYMENT_FORM,
    capabilityKeys: requiredCapabilities.map((capability) => capability.capability),
  };
}

export function buildDeploymentForm(
  deployment: PlatformDeploymentProfile,
  requiredCapabilities: PlatformCapability[] = [],
): DeploymentFormState {
  return {
    slug: deployment.slug,
    displayName: deployment.display_name,
    description: deployment.description,
    capabilityKeys: uniqueCapabilityKeys([
      ...requiredCapabilities.map((capability) => capability.capability),
      ...deployment.bindings.map((binding) => binding.capability),
    ]),
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
  capabilitiesToValidate: PlatformCapability[],
  form: DeploymentFormState,
  options: DeploymentFormValidationOptions,
): string | null {
  const missingBinding = capabilitiesToValidate.find((capability) => !form.providerIdsByCapability[capability.capability]);
  if (missingBinding) {
    return options.bindingRequiredMessage;
  }

  const incompleteModelBinding = capabilitiesToValidate.find((capability) => {
    if (!capabilityRequiresModelResource(capability.capability)) {
      return false;
    }
    return (form.resourceIdsByCapability[capability.capability] ?? []).length === 0;
  });
  if (incompleteModelBinding) {
    return options.resourceRequiredMessage?.(incompleteModelBinding)
      ?? `${incompleteModelBinding.display_name} requires at least one bound resource.`;
  }

  const missingDefaultModelBinding = capabilitiesToValidate.find((capability) => {
    if (!capabilityRequiresModelResource(capability.capability)) {
      return false;
    }
    const resourceIds = form.resourceIdsByCapability[capability.capability] ?? [];
    const defaultResourceId = form.defaultResourceIdsByCapability[capability.capability] ?? "";
    return !defaultResourceId || !resourceIds.includes(defaultResourceId);
  });
  if (missingDefaultModelBinding) {
    return options.defaultResourceRequiredMessage?.(missingDefaultModelBinding)
      ?? `${missingDefaultModelBinding.display_name} requires a default resource.`;
  }

  if (options.providersByCapability && options.modelResourcesByCapability) {
    for (const capability of capabilitiesToValidate) {
      if (!capabilityRequiresModelResource(capability.capability)) {
        continue;
      }
      const providerId = form.providerIdsByCapability[capability.capability] ?? "";
      const provider = (options.providersByCapability[capability.capability] ?? [])
        .find((item) => item.id === providerId);
      if (!provider) {
        continue;
      }
      const models = options.modelResourcesByCapability[capability.capability] ?? [];
      const modelsById = new Map(models.map((model) => [model.id, model]));
      const compatibleModelIds = new Set(filterModelsForProviderOrigin(models, provider).map((model) => model.id));
      const incompatibleResourceNames = (form.resourceIdsByCapability[capability.capability] ?? [])
        .filter((resourceId) => !compatibleModelIds.has(resourceId))
        .map((resourceId) => modelsById.get(resourceId)?.name || resourceId);
      if (incompatibleResourceNames.length > 0) {
        return options.resourceCompatibilityMessage?.(capability, provider, incompatibleResourceNames)
          ?? `${capability.display_name} has resources that cannot be served by ${provider.display_name}.`;
      }
    }
  }

  const invalidVectorBinding = capabilitiesToValidate.find((capability) => {
    if (capability.capability !== "vector_store") {
      return false;
    }
    const policy = form.resourcePolicyByCapability[capability.capability] ?? {};
    const selectionMode = String(policy.selection_mode ?? "explicit");
    if (selectionMode === "dynamic_namespace") {
      return !String(policy.namespace_prefix ?? "").trim();
    }
    return false;
  });
  if (invalidVectorBinding) {
    return `${invalidVectorBinding.display_name} requires a namespace prefix for dynamic namespace mode.`;
  }

  return null;
}

export function buildDeploymentIdentityMutationInput(
  form: DeploymentFormState,
): PlatformDeploymentIdentityMutationInput {
  return {
    slug: form.slug,
    display_name: form.displayName,
    description: form.description,
  };
}


export function buildDeploymentBindingMutationInput(
  capability: PlatformCapability,
  form: DeploymentFormState,
  knowledgeBases: KnowledgeBase[],
): PlatformDeploymentBindingMutationInput {
  const knowledgeBasesById = new Map(knowledgeBases.map((knowledgeBase) => [knowledgeBase.id, knowledgeBase]));
  return {
    provider_id: form.providerIdsByCapability[capability.capability],
    resources: capability.capability === "vector_store"
      ? (form.resourceIdsByCapability[capability.capability] ?? []).map((resourceId) => {
          const knowledgeBase = knowledgeBasesById.get(resourceId);
          if (knowledgeBase) {
            return {
              id: knowledgeBase.id,
              resource_kind: "knowledge_base",
              ref_type: "knowledge_base",
              knowledge_base_id: knowledgeBase.id,
              provider_resource_id: knowledgeBase.index_name,
              display_name: knowledgeBase.display_name,
              metadata: {
                slug: knowledgeBase.slug,
                index_name: knowledgeBase.index_name,
                lifecycle_state: knowledgeBase.lifecycle_state,
                sync_status: knowledgeBase.sync_status,
                document_count: knowledgeBase.document_count,
              },
            };
          }
          return {
            id: resourceId,
            resource_kind: "index",
            ref_type: "provider_resource",
            provider_resource_id: resourceId,
            display_name: resourceId,
            metadata: {},
          };
        })
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
  };
}

export function buildDeploymentMutationInput(
  capabilitiesToInclude: PlatformCapability[],
  form: DeploymentFormState,
  knowledgeBases: KnowledgeBase[],
): PlatformDeploymentMutationInput {
  return {
    ...buildDeploymentIdentityMutationInput(form),
    bindings: capabilitiesToInclude.map((capability) => ({
      capability: capability.capability,
      ...buildDeploymentBindingMutationInput(capability, form, knowledgeBases),
    })),
  };
}

export function addCapabilityToDeploymentForm(
  form: DeploymentFormState,
  capabilityKey: string,
): DeploymentFormState {
  if (!capabilityKey || form.capabilityKeys.includes(capabilityKey)) {
    return form;
  }
  return {
    ...form,
    capabilityKeys: [...form.capabilityKeys, capabilityKey],
  };
}

export function getVisibleDeploymentCapabilities(
  allCapabilities: PlatformCapability[],
  form: DeploymentFormState,
): PlatformCapability[] {
  const includedKeys = new Set(form.capabilityKeys);
  return allCapabilities.filter((capability) => includedKeys.has(capability.capability));
}

export function getAvailableDeploymentCapabilities(
  allCapabilities: PlatformCapability[],
  form: DeploymentFormState,
): PlatformCapability[] {
  const includedKeys = new Set(form.capabilityKeys);
  return allCapabilities.filter((capability) => !includedKeys.has(capability.capability));
}

export function getConfiguredOptionalDeploymentCapabilities(
  allCapabilities: PlatformCapability[],
  requiredCapabilities: PlatformCapability[],
  form: DeploymentFormState,
): PlatformCapability[] {
  const requiredCapabilityKeys = new Set(requiredCapabilities.map((capability) => capability.capability));
  const includedKeys = new Set(form.capabilityKeys);
  return allCapabilities.filter((capability) =>
    includedKeys.has(capability.capability)
    && !requiredCapabilityKeys.has(capability.capability)
    && Boolean(form.providerIdsByCapability[capability.capability]),
  );
}
