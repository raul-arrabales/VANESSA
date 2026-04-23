import { useCallback, useMemo } from "react";
import type { TFunction } from "i18next";
import type { KnowledgeBase } from "../../../api/context";
import type { ManagedModel } from "../../../api/modelops";
import type {
  PlatformCapability,
  PlatformDeploymentMutationInput,
  PlatformDeploymentProfile,
  PlatformProvider,
} from "../../../api/platform";
import {
  buildCloneForm,
  buildDeploymentForm,
  buildDeploymentMutationInput,
  createDefaultDeploymentForm,
  getConfiguredOptionalDeploymentCapabilities,
  getCapabilityProviders,
  getManagedModelsByCapability,
  validateDeploymentForm,
  type DeploymentCloneFormState,
  type DeploymentFormState,
} from "../deploymentEditor";

type UsePlatformDeploymentEditorParams = {
  mode: "create" | "edit";
  capabilities: PlatformCapability[];
  providers: PlatformProvider[];
  eligibleModelsByCapability: Record<string, ManagedModel[]>;
  knowledgeBases: KnowledgeBase[];
  t: TFunction<"common">;
  deployment?: PlatformDeploymentProfile | null;
};

type UsePlatformDeploymentEditorResult = {
  capabilities: PlatformCapability[];
  requiredCapabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  buildInitialForm: () => DeploymentFormState;
  buildInitialCloneForm: () => DeploymentCloneFormState | null;
  validateAndBuildMutation: (form: DeploymentFormState) => {
    validationError: string | null;
    mutationInput: PlatformDeploymentMutationInput | null;
  };
};

export function usePlatformDeploymentEditor({
  mode,
  capabilities,
  providers,
  eligibleModelsByCapability,
  knowledgeBases,
  t,
  deployment = null,
}: UsePlatformDeploymentEditorParams): UsePlatformDeploymentEditorResult {
  const requiredCapabilities = useMemo(
    () => capabilities.filter((capability) => capability.required),
    [capabilities],
  );
  const providersByCapability = useMemo(
    () => getCapabilityProviders(providers, capabilities),
    [capabilities, providers],
  );
  const modelResourcesByCapability = useMemo(
    () => getManagedModelsByCapability(eligibleModelsByCapability, capabilities),
    [capabilities, eligibleModelsByCapability],
  );

  const buildInitialForm = useCallback(
    (): DeploymentFormState => (
      mode === "edit" && deployment ? buildDeploymentForm(deployment, requiredCapabilities) : createDefaultDeploymentForm(requiredCapabilities)
    ),
    [deployment, mode, requiredCapabilities],
  );

  const buildInitialCloneForm = useCallback(
    (): DeploymentCloneFormState | null => (
      mode === "edit" && deployment ? buildCloneForm(deployment) : null
    ),
    [deployment, mode],
  );

  const validateAndBuildMutation = useCallback(
    (form: DeploymentFormState) => {
      const configuredOptionalCapabilities = getConfiguredOptionalDeploymentCapabilities(capabilities, requiredCapabilities, form);
      const capabilitiesToPersist = [...requiredCapabilities, ...configuredOptionalCapabilities];
      const validationError = validateDeploymentForm(capabilitiesToPersist, form, {
        bindingRequiredMessage: t("platformControl.feedback.bindingRequired"),
        resourceRequiredMessage: (capability) =>
          t("platformControl.feedback.resourceRequired", { capability: capability.display_name }),
        defaultResourceRequiredMessage: (capability) =>
          t("platformControl.feedback.defaultResourceRequired", { capability: capability.display_name }),
        resourceCompatibilityMessage: (capability, provider, resourceNames) =>
          t("platformControl.feedback.resourceProviderMismatch", {
            capability: capability.display_name,
            provider: provider.display_name,
            origin: t(`platformControl.badges.${provider.provider_origin}`),
            resources: resourceNames.join(", "),
          }),
        providersByCapability,
        modelResourcesByCapability,
      });

      return {
        validationError,
        mutationInput: validationError ? null : buildDeploymentMutationInput(capabilitiesToPersist, form, knowledgeBases),
      };
    },
    [capabilities, knowledgeBases, modelResourcesByCapability, providersByCapability, requiredCapabilities, t],
  );

  return {
    capabilities,
    requiredCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    buildInitialCloneForm,
    validateAndBuildMutation,
  };
}
