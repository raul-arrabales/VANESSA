import { useState } from "react";
import type { NavigateFunction } from "react-router-dom";
import type { TFunction } from "i18next";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  deleteDeploymentProfile,
  deleteDeploymentBinding,
  patchDeploymentProfileIdentity,
  upsertDeploymentBinding,
  type PlatformCapability,
  type PlatformDeploymentProfile,
  type PlatformProvider,
} from "../../../api/platform";
import type { KnowledgeBase } from "../../../api/context";
import { withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { withDeploymentSeedState } from "../deploymentRouteState";
import {
  buildDeploymentBindingMutationInput,
  buildDeploymentForm,
  buildDeploymentIdentityMutationInput,
  validateDeploymentForm,
  type DeploymentCloneFormState,
  type DeploymentFormState,
} from "../deploymentEditor";
import type { ManagedModel } from "../../../api/modelops";
import { formatActivationValidationError } from "../validationFeedback";

type UsePlatformDeploymentDetailMutationsParams = {
  token: string;
  deployment: PlatformDeploymentProfile | null;
  form: DeploymentFormState | null;
  cloneForm: DeploymentCloneFormState | null;
  knowledgeBases: KnowledgeBase[];
  capabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  setLocalDeployment: React.Dispatch<React.SetStateAction<PlatformDeploymentProfile | null>>;
  setForm: React.Dispatch<React.SetStateAction<DeploymentFormState | null>>;
  reload: () => Promise<void>;
  navigate: NavigateFunction;
  showErrorFeedback: (errorOrMessage: unknown, fallbackMessage?: string) => void;
  showSuccessFeedback: (message: string) => void;
  t: TFunction<"common">;
};

type UsePlatformDeploymentDetailMutationsResult = {
  errorMessage: string;
  savingIdentity: boolean;
  savingCapabilityKeys: Record<string, boolean>;
  cloning: boolean;
  activating: boolean;
  confirmActivate: boolean;
  confirmDelete: boolean;
  bindingToRemove: string | null;
  removingBindingKey: string | null;
  setConfirmActivate: React.Dispatch<React.SetStateAction<boolean>>;
  setConfirmDelete: React.Dispatch<React.SetStateAction<boolean>>;
  setBindingToRemove: React.Dispatch<React.SetStateAction<string | null>>;
  handleSaveIdentity: () => Promise<void>;
  handleSaveCapability: (capabilityKey: string) => Promise<void>;
  handleClone: () => Promise<void>;
  handleActivate: () => Promise<void>;
  handleDelete: () => Promise<void>;
  handleRemoveBinding: () => Promise<void>;
};

export function usePlatformDeploymentDetailMutations({
  token,
  deployment,
  form,
  cloneForm,
  knowledgeBases,
  capabilities,
  providersByCapability,
  modelResourcesByCapability,
  setLocalDeployment,
  setForm,
  reload,
  navigate,
  showErrorFeedback,
  showSuccessFeedback,
  t,
}: UsePlatformDeploymentDetailMutationsParams): UsePlatformDeploymentDetailMutationsResult {
  const [errorMessage, setErrorMessage] = useState("");
  const [savingIdentity, setSavingIdentity] = useState(false);
  const [savingCapabilityKeys, setSavingCapabilityKeys] = useState<Record<string, boolean>>({});
  const [cloning, setCloning] = useState(false);
  const [activating, setActivating] = useState(false);
  const [confirmActivate, setConfirmActivate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [bindingToRemove, setBindingToRemove] = useState<string | null>(null);
  const [removingBindingKey, setRemovingBindingKey] = useState<string | null>(null);

  async function handleSaveIdentity(): Promise<void> {
    if (!token || !deployment || !form) {
      return;
    }

    setSavingIdentity(true);
    setErrorMessage("");
    try {
      const updated = await patchDeploymentProfileIdentity(
        deployment.id,
        buildDeploymentIdentityMutationInput(form),
        token,
      );
      setLocalDeployment(updated);
      showSuccessFeedback(t("platformControl.feedback.deploymentUpdated", { name: form.displayName }));
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSavingIdentity(false);
    }
  }

  async function handleSaveCapability(capabilityKey: string): Promise<void> {
    if (!token || !deployment || !form) {
      return;
    }
    const capability = capabilities.find((item) => item.capability === capabilityKey);
    if (!capability) {
      return;
    }
    if (!form.providerIdsByCapability[capabilityKey]) {
      showErrorFeedback(
        t("platformControl.feedback.capabilityProviderRequired", { capability: capability.display_name }),
        t("platformControl.feedback.deploymentSaveFailed"),
      );
      return;
    }
    const validationError = validateDeploymentForm([capability], form, {
      bindingRequiredMessage: t("platformControl.feedback.bindingRequired"),
      resourceRequiredMessage: (item) =>
        t("platformControl.feedback.resourceRequired", { capability: item.display_name }),
      defaultResourceRequiredMessage: (item) =>
        t("platformControl.feedback.defaultResourceRequired", { capability: item.display_name }),
      resourceCompatibilityMessage: (item, provider, resourceNames) =>
        t("platformControl.feedback.resourceProviderMismatch", {
          capability: item.display_name,
          provider: provider.display_name,
          origin: t(`platformControl.badges.${provider.provider_origin}`),
          resources: resourceNames.join(", "),
        }),
      providersByCapability,
      modelResourcesByCapability,
    });
    if (validationError) {
      showErrorFeedback(validationError, t("platformControl.feedback.deploymentSaveFailed"));
      return;
    }

    setSavingCapabilityKeys((current) => ({ ...current, [capabilityKey]: true }));
    setErrorMessage("");
    try {
      const updated = await upsertDeploymentBinding(
        deployment.id,
        capabilityKey,
        buildDeploymentBindingMutationInput(capability, form, knowledgeBases, modelResourcesByCapability),
        token,
      );
      setLocalDeployment(updated);
      showSuccessFeedback(
        t("platformControl.feedback.deploymentBindingUpdated", {
          capability: capability.display_name,
          name: updated.display_name,
        }),
      );
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSavingCapabilityKeys((current) => ({ ...current, [capabilityKey]: false }));
    }
  }

  async function handleClone(): Promise<void> {
    if (!token || !deployment || !cloneForm) {
      return;
    }

    setCloning(true);
    setErrorMessage("");
    try {
      const cloned = await cloneDeploymentProfile(
        deployment.id,
        {
          slug: cloneForm.slug,
          display_name: cloneForm.displayName,
          description: cloneForm.description,
        },
        token,
      );
      navigate(`/control/platform/deployments/${cloned.id}`, {
        state: withDeploymentSeedState(
          cloned,
          withActionFeedbackState({
            kind: "success",
            message: t("platformControl.feedback.deploymentCloned", { name: cloned.display_name }),
          }),
        ),
      });
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setCloning(false);
    }
  }

  async function handleActivate(): Promise<void> {
    if (!token || !deployment) {
      return;
    }

    setActivating(true);
    setErrorMessage("");
    try {
      const updated = await activateDeploymentProfile(deployment.id, token);
      setLocalDeployment(updated);
      showSuccessFeedback(t("platformControl.feedback.activationSuccess", { name: deployment.display_name }));
      await reload();
    } catch (error) {
      showErrorFeedback(formatActivationValidationError(error) ?? error, t("platformControl.feedback.activationFailed"));
    } finally {
      setActivating(false);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!token || !deployment) {
      return;
    }

    setErrorMessage("");
    try {
      await deleteDeploymentProfile(deployment.id, token);
      navigate("/control/platform/deployments", {
        state: withActionFeedbackState({
          kind: "success",
          message: t("platformControl.feedback.deploymentDeleted"),
        }),
      });
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentDeleteFailed"));
    }
  }

  async function handleRemoveBinding(): Promise<void> {
    if (!token || !deployment || !bindingToRemove || removingBindingKey) {
      return;
    }
    const capability = capabilities.find((item) => item.capability === bindingToRemove);
    setRemovingBindingKey(bindingToRemove);
    setErrorMessage("");
    try {
      const updated = await deleteDeploymentBinding(deployment.id, bindingToRemove, token);
      setLocalDeployment(updated);
      setForm(buildDeploymentForm(updated, capabilities.filter((item) => item.required)));
      setBindingToRemove(null);
      showSuccessFeedback(t("platformControl.feedback.deploymentBindingRemoved", {
        capability: capability?.display_name ?? bindingToRemove,
        name: updated.display_name,
      }));
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentBindingRemoveFailed"));
    } finally {
      setRemovingBindingKey(null);
    }
  }

  return {
    errorMessage,
    savingIdentity,
    savingCapabilityKeys,
    cloning,
    activating,
    confirmActivate,
    confirmDelete,
    bindingToRemove,
    removingBindingKey,
    setConfirmActivate,
    setConfirmDelete,
    setBindingToRemove,
    handleSaveIdentity,
    handleSaveCapability,
    handleClone,
    handleActivate,
    handleDelete,
    handleRemoveBinding,
  };
}
