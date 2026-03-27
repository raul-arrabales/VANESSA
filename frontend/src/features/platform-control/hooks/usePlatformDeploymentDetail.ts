import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  activateDeploymentProfile,
  cloneDeploymentProfile,
  deleteDeploymentProfile,
  updateDeploymentProfile,
} from "../../../api/platform";
import { useActionFeedback, useRouteActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import type { DeploymentCloneFormState, DeploymentFormState } from "../deploymentEditor";
import { readDeploymentSeedFromState, withDeploymentSeedState } from "../deploymentRouteState";
import { usePlatformDeploymentEditor } from "./usePlatformDeploymentEditor";
import { usePlatformDeploymentEditorData } from "./usePlatformDeploymentEditorData";

type UsePlatformDeploymentDetailOptions = {
  deploymentId: string;
  token: string;
};

export function usePlatformDeploymentDetail({
  deploymentId,
  token,
}: UsePlatformDeploymentDetailOptions) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const location = useLocation();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const {
    state,
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    deployments,
    activationAudit,
    eligibleModelsByCapability,
    knowledgeBases,
    reload,
  } = usePlatformDeploymentEditorData(token);
  const [form, setForm] = useState<DeploymentFormState | null>(null);
  const [cloneForm, setCloneForm] = useState<DeploymentCloneFormState | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [activating, setActivating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const seedReloadedDeploymentIdRef = useRef<string>("");

  const fetchedDeployment = deployments.find((item) => item.id === deploymentId) ?? null;
  const seededDeployment = readDeploymentSeedFromState(location.state, deploymentId);
  const deployment = fetchedDeployment ?? seededDeployment;
  const capabilityLabelByKey = useMemo(
    () => new Map(capabilities.map((capability) => [capability.capability, capability.display_name])),
    [capabilities],
  );
  const {
    requiredCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    buildInitialCloneForm,
    validateAndBuildMutation,
  } = usePlatformDeploymentEditor({
    mode: "edit",
    capabilities,
    providers,
    eligibleModelsByCapability,
    knowledgeBases,
    deployment,
    t,
  });
  const deploymentAudit = activationAudit.filter((entry) => entry.deployment_profile.id === deploymentId);

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (deployment) {
      setForm(buildInitialForm());
      setCloneForm(buildInitialCloneForm());
    }
  }, [buildInitialCloneForm, buildInitialForm, deployment]);

  useEffect(() => {
    if (!seededDeployment || fetchedDeployment) {
      seedReloadedDeploymentIdRef.current = "";
      return;
    }
    if (seedReloadedDeploymentIdRef.current === seededDeployment.id) {
      return;
    }

    seedReloadedDeploymentIdRef.current = seededDeployment.id;
    void reload();
  }, [fetchedDeployment, reload, seededDeployment]);

  async function handleSave(): Promise<void> {
    if (!token || !deployment || !form) {
      return;
    }

    const { validationError, mutationInput } = validateAndBuildMutation(form);
    if (validationError) {
      showErrorFeedback(validationError, t("platformControl.feedback.deploymentSaveFailed"));
      return;
    }

    setSaving(true);
    setErrorMessage("");
    try {
      await updateDeploymentProfile(deployment.id, mutationInput!, token);
      showSuccessFeedback(t("platformControl.feedback.deploymentUpdated", { name: form.displayName }));
      await reload();
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSaving(false);
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
      await activateDeploymentProfile(deployment.id, token);
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
    activationAudit,
    activating,
    capabilities,
    capabilityLabelByKey,
    cloneForm,
    cloning,
    confirmDelete,
    deployment,
    deploymentAudit,
    deployments,
    errorMessage,
    form,
    knowledgeBases,
    loadErrorMessage,
    modelResourcesByCapability,
    providers,
    providersByCapability,
    requiredCapabilities,
    saving,
    setCloneForm,
    setConfirmDelete,
    setForm,
    state,
    handleActivate,
    handleClone,
    handleDelete,
    handleSave,
    resetForm: () => deployment ? setForm(buildInitialForm()) : undefined,
  };
}
