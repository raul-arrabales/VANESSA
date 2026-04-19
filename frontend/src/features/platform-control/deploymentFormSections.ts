import type { ManagedModel } from "../../api/modelops";
import type { KnowledgeBase } from "../../api/context";
import type { PlatformCapability, PlatformProvider } from "../../api/platform";
import type { DeploymentFormState } from "./deploymentEditor";
import { getDeploymentCapabilityMode } from "./capabilities";
import { filterModelsForProviderOrigin } from "./deploymentModelCompatibility";

type Translate = (key: string, options?: Record<string, unknown>) => string;

export type DeploymentCapabilitySectionMode = "model" | "vector" | "none";

export type DeploymentModelCheckboxOption = {
  id: string;
  name: string;
  selected: boolean;
};

export type DeploymentCapabilitySectionState = {
  capability: PlatformCapability;
  capabilityKey: string;
  capabilityMode: DeploymentCapabilitySectionMode;
  capabilityProviders: PlatformProvider[];
  selectedProviderId: string;
  selectedProvider: PlatformProvider | null;
  modelOptions: ManagedModel[];
  modelCheckboxOptions: DeploymentModelCheckboxOption[];
  selectedResourceIds: string[];
  availableDefaultResources: ManagedModel[];
  vectorDefaultResources: KnowledgeBase[];
  defaultResourceId: string;
  resourcePickerSummary: string;
  loadedModelEligibilityHint: string | null;
  noEligibleResourcesHint: string | null;
  vectorSelectionMode: string;
  namespacePrefix: string;
  vectorKnowledgeBases: KnowledgeBase[];
  configurationStatus?: {
    is_ready: boolean;
    issues: Array<{
      code: string;
      message: string;
    }>;
    summary: string;
  } | null;
};

type BuildDeploymentCapabilitySectionStateParams = {
  capability: PlatformCapability;
  value: DeploymentFormState;
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  knowledgeBases: KnowledgeBase[];
  bindingStatusByCapability?: Record<
    string,
    {
      is_ready: boolean;
      issues: Array<{
        code: string;
        message: string;
      }>;
      summary: string;
    } | undefined
  >;
  t: Translate;
};

function getModelDisplayName(model: ManagedModel): string {
  return model.name.trim() || model.id;
}

function getKnowledgeBaseDisplayName(knowledgeBase: KnowledgeBase): string {
  return knowledgeBase.display_name.trim() || knowledgeBase.slug || knowledgeBase.id;
}

function buildResourcePickerSummary(
  selectedResourceIds: string[],
  resourceOptions: Array<{ id: string; name: string }>,
  t: Translate,
): string {
  if (selectedResourceIds.length === 0) {
    return t("platformControl.forms.deployment.resourcePickerEmpty");
  }

  const namesById = new Map(resourceOptions.map((resource) => [resource.id, resource.name]));
  const selectedNames = selectedResourceIds.map((resourceId) => namesById.get(resourceId) ?? resourceId);

  if (selectedNames.length <= 2) {
    return selectedNames.join(", ");
  }

  return t("platformControl.forms.deployment.resourcePickerSummary", {
    first: selectedNames[0],
    count: selectedNames.length - 1,
  });
}

export function buildDeploymentCapabilitySectionState({
  capability,
  value,
  providersByCapability,
  modelResourcesByCapability,
  knowledgeBases,
  bindingStatusByCapability = {},
  t,
}: BuildDeploymentCapabilitySectionStateParams): DeploymentCapabilitySectionState {
  const capabilityKey = capability.capability;
  const capabilityMode = getDeploymentCapabilityMode(capabilityKey);
  const capabilityProviders = providersByCapability[capabilityKey] ?? [];
  const selectedProviderId = value.providerIdsByCapability[capabilityKey] ?? "";
  const selectedProvider = capabilityProviders.find((provider) => provider.id === selectedProviderId) ?? null;
  const allModelOptions = capabilityMode === "model" ? (modelResourcesByCapability[capabilityKey] ?? []) : [];
  const modelOptions = filterModelsForProviderOrigin(allModelOptions, selectedProvider);
  const selectedResourceIds = value.resourceIdsByCapability[capabilityKey] ?? [];
  const modelCheckboxOptions = modelOptions.map((model) => ({
    id: model.id,
    name: getModelDisplayName(model),
    selected: selectedResourceIds.includes(model.id),
  }));
  const vectorKnowledgeBases = capabilityMode === "vector" ? knowledgeBases : [];
  const availableDefaultResources = modelOptions.filter((model) => selectedResourceIds.includes(model.id));
  const vectorDefaultResources = vectorKnowledgeBases.filter((knowledgeBase) => selectedResourceIds.includes(knowledgeBase.id));
  const loadedManagedModelId = selectedProvider?.loaded_managed_model_id ?? null;
  const loadedManagedModelName = selectedProvider?.loaded_managed_model_name ?? loadedManagedModelId ?? "";
  const loadedModelIsEligible = loadedManagedModelId
    ? modelOptions.some((model) => model.id === loadedManagedModelId)
    : false;
  const loadedModelEligibilityHint = capabilityMode === "model"
    && modelOptions.length === 0
    && Boolean(loadedManagedModelId)
    && !loadedModelIsEligible
    ? t("platformControl.forms.deployment.loadedModelNotEligibleHint", {
        capability: capability.display_name,
        provider: selectedProvider?.display_name ?? t("platformControl.summary.none"),
        model: loadedManagedModelName,
      })
    : null;
  const noEligibleResourcesHint = capabilityMode === "model"
    && modelOptions.length === 0
    && !loadedModelEligibilityHint
    ? t("platformControl.forms.deployment.noEligibleResourcesHint", {
        capability: capability.display_name,
      })
    : null;
  const vectorPolicy = value.resourcePolicyByCapability[capabilityKey] ?? {};
  return {
    capability,
    capabilityKey,
    capabilityMode,
    capabilityProviders,
    selectedProviderId,
    selectedProvider,
    modelOptions,
    modelCheckboxOptions,
    selectedResourceIds,
    availableDefaultResources,
    vectorDefaultResources,
    defaultResourceId: value.defaultResourceIdsByCapability[capabilityKey] ?? "",
    resourcePickerSummary: capabilityMode === "vector"
      ? buildResourcePickerSummary(
          selectedResourceIds,
          vectorKnowledgeBases.map((knowledgeBase) => ({
            id: knowledgeBase.id,
            name: getKnowledgeBaseDisplayName(knowledgeBase),
          })),
          t,
        )
      : buildResourcePickerSummary(
          selectedResourceIds,
          modelOptions.map((model) => ({
            id: model.id,
            name: getModelDisplayName(model),
          })),
          t,
        ),
    loadedModelEligibilityHint,
    noEligibleResourcesHint,
    vectorSelectionMode: String(vectorPolicy.selection_mode ?? "explicit"),
    namespacePrefix: String(vectorPolicy.namespace_prefix ?? ""),
    vectorKnowledgeBases,
    configurationStatus: bindingStatusByCapability[capabilityKey] ?? null,
  };
}
