import { useState } from "react";
import type { NavigateFunction } from "react-router-dom";
import type { TFunction } from "i18next";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  deleteDeploymentProfile,
  patchDeploymentProfileIdentity,
  upsertDeploymentBinding,
  type PlatformCapability,
  type PlatformDeploymentProfile,
} from "../../../api/platform";
import type { KnowledgeBase } from "../../../api/context";
import { withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { withDeploymentSeedState } from "../deploymentRouteState";
import {
  buildDeploymentBindingMutationInput,
  buildDeploymentIdentityMutationInput,
  type DeploymentCloneFormState,
  type DeploymentFormState,
} from "../deploymentEditor";

type UsePlatformDeploymentDetailMutationsParams = {
  token: string;
  deployment: PlatformDeploymentProfile | null;
  form: DeploymentFormState | null;
  cloneForm: DeploymentCloneFormState | null;
  knowledgeBases: KnowledgeBase[];
  requiredCapabilities: PlatformCapability[];
  setLocalDeployment: React.Dispatch<React.SetStateAction<PlatformDeploymentProfile | null>>;
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
  setConfirmActivate: React.Dispatch<React.SetStateAction<boolean>>;
  setConfirmDelete: React.Dispatch<React.SetStateAction<boolean>>;
  handleSaveIdentity: () => Promise<void>;
  handleSaveCapability: (capabilityKey: string) => Promise<void>;
  handleClone: () => Promise<void>;
  handleActivate: () => Promise<void>;
  handleDelete: () => Promise<void>;
};

export function usePlatformDeploymentDetailMutations({
  token,
  deployment,
  form,
  cloneForm,
  knowledgeBases,
  requiredCapabilities,
  setLocalDeployment,
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
    const capability = requiredCapabilities.find((item) => item.capability === capabilityKey);
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

    setSavingCapabilityKeys((current) => ({ ...current, [capabilityKey]: true }));
    setErrorMessage("");
    try {
      const updated = await upsertDeploymentBinding(
        deployment.id,
        capabilityKey,
        buildDeploymentBindingMutationInput(capability, form, knowledgeBases),
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
      showErrorFeedback(error, t("platformControl.feedback.activationFailed"));
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

  return {
    errorMessage,
    savingIdentity,
    savingCapabilityKeys,
    cloning,
    activating,
    confirmActivate,
    confirmDelete,
    setConfirmActivate,
    setConfirmDelete,
    handleSaveIdentity,
    handleSaveCapability,
    handleClone,
    handleActivate,
    handleDelete,
  };
}
