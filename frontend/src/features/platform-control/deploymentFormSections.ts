import type { ManagedModel } from "../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../api/platform";
import type { DeploymentFormState } from "./deploymentEditor";
import {
  getDeploymentCapabilityMode,
} from "./utils";

type Translate = (key: string, options?: Record<string, unknown>) => string;

export type DeploymentCapabilitySectionMode = "model" | "vector" | "none";

export type DeploymentCapabilitySectionState = {
  capability: PlatformCapability;
  capabilityKey: string;
  capabilityMode: DeploymentCapabilitySectionMode;
  capabilityProviders: PlatformProvider[];
  selectedProviderId: string;
  selectedProvider: PlatformProvider | null;
  modelOptions: ManagedModel[];
  selectedResourceIds: string[];
  availableDefaultResources: ManagedModel[];
  defaultResourceId: string;
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
    selectedResourceIds,
    availableDefaultResources,
    defaultResourceId: value.defaultResourceIdsByCapability[capabilityKey] ?? "",
    loadedModelEligibilityHint,
    noEligibleResourcesHint,
    vectorSelectionMode: String(vectorPolicy.selection_mode ?? "explicit"),
    namespacePrefix: String(vectorPolicy.namespace_prefix ?? ""),
  };
}
