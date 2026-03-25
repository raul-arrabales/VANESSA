import { useCallback, useMemo } from "react";
import type { TFunction } from "i18next";
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
  DEFAULT_DEPLOYMENT_FORM,
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
  t: TFunction<"common">;
  deployment?: PlatformDeploymentProfile | null;
};

type UsePlatformDeploymentEditorResult = {
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
  t,
  deployment = null,
}: UsePlatformDeploymentEditorParams): UsePlatformDeploymentEditorResult {
  const requiredCapabilities = useMemo(
    () => capabilities.filter((capability) => capability.required),
    [capabilities],
  );
  const providersByCapability = useMemo(
    () => getCapabilityProviders(providers, requiredCapabilities),
    [providers, requiredCapabilities],
  );
  const modelResourcesByCapability = useMemo(
    () => getManagedModelsByCapability(eligibleModelsByCapability, requiredCapabilities),
    [eligibleModelsByCapability, requiredCapabilities],
  );

  const buildInitialForm = useCallback(
    (): DeploymentFormState => (
      mode === "edit" && deployment ? buildDeploymentForm(deployment) : DEFAULT_DEPLOYMENT_FORM
    ),
    [deployment, mode],
  );

  const buildInitialCloneForm = useCallback(
    (): DeploymentCloneFormState | null => (
      mode === "edit" && deployment ? buildCloneForm(deployment) : null
    ),
    [deployment, mode],
  );

  const validateAndBuildMutation = useCallback(
    (form: DeploymentFormState) => {
      const validationError = validateDeploymentForm(requiredCapabilities, form, {
        bindingRequiredMessage: t("platformControl.feedback.bindingRequired"),
        resourceRequiredMessage: (capabilityDisplayName) =>
          t("platformControl.feedback.resourceRequired", { capability: capabilityDisplayName }),
        defaultResourceRequiredMessage: (capabilityDisplayName) =>
          t("platformControl.feedback.defaultResourceRequired", { capability: capabilityDisplayName }),
      });

      return {
        validationError,
        mutationInput: validationError ? null : buildDeploymentMutationInput(requiredCapabilities, form),
      };
    },
    [requiredCapabilities, t],
  );

  return {
    requiredCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    buildInitialCloneForm,
    validateAndBuildMutation,
  };
}
