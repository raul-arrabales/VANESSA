import type { ManagedModel } from "../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../api/platform";
import type { DeploymentFormState } from "./deploymentEditor";
import { getDeploymentCapabilityMode } from "./capabilities";

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
  defaultResourceId: string;
  resourcePickerSummary: string;
  loadedModelEligibilityHint: string | null;
  noEligibleResourcesHint: string | null;
  vectorSelectionMode: string;
  namespacePrefix: string;
};

type BuildDeploymentCapabilitySectionStateParams = {
  capability: PlatformCapability;
  value: DeploymentFormState;
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  t: Translate;
};

function getModelDisplayName(model: ManagedModel): string {
  return model.name.trim() || model.id;
}

function buildResourcePickerSummary(
  selectedResourceIds: string[],
  modelOptions: ManagedModel[],
  t: Translate,
): string {
  if (selectedResourceIds.length === 0) {
    return t("platformControl.forms.deployment.resourcePickerEmpty");
  }

  const namesById = new Map(modelOptions.map((model) => [model.id, getModelDisplayName(model)]));
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
  t,
}: BuildDeploymentCapabilitySectionStateParams): DeploymentCapabilitySectionState {
  const capabilityKey = capability.capability;
  const capabilityMode = getDeploymentCapabilityMode(capabilityKey);
  const capabilityProviders = providersByCapability[capabilityKey] ?? [];
  const selectedProviderId = value.providerIdsByCapability[capabilityKey] ?? "";
  const selectedProvider = capabilityProviders.find((provider) => provider.id === selectedProviderId) ?? null;
  const modelOptions = capabilityMode === "model" ? (modelResourcesByCapability[capabilityKey] ?? []) : [];
  const selectedResourceIds = value.resourceIdsByCapability[capabilityKey] ?? [];
  const modelCheckboxOptions = modelOptions.map((model) => ({
    id: model.id,
    name: getModelDisplayName(model),
    selected: selectedResourceIds.includes(model.id),
  }));
  const availableDefaultResources = modelOptions.filter((model) => selectedResourceIds.includes(model.id));
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
    defaultResourceId: value.defaultResourceIdsByCapability[capabilityKey] ?? "",
    resourcePickerSummary: buildResourcePickerSummary(selectedResourceIds, modelOptions, t),
    loadedModelEligibilityHint,
    noEligibleResourcesHint,
    vectorSelectionMode: String(vectorPolicy.selection_mode ?? "explicit"),
    namespacePrefix: String(vectorPolicy.namespace_prefix ?? ""),
  };
}
