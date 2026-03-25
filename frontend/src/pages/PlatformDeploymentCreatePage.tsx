import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createDeploymentProfile } from "../api/platform";
import { useAuth } from "../auth/AuthProvider";
import PlatformDeploymentForm from "../features/platform-control/components/PlatformDeploymentForm";
import type { DeploymentFormState } from "../features/platform-control/deploymentEditor";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import { usePlatformDeploymentEditor } from "../features/platform-control/hooks/usePlatformDeploymentEditor";
import { usePlatformDeploymentEditorData } from "../features/platform-control/hooks/usePlatformDeploymentEditorData";

export default function PlatformDeploymentCreatePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const navigate = useNavigate();
  const {
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    eligibleModelsByCapability,
  } = usePlatformDeploymentEditorData(token);
  const {
    requiredCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    validateAndBuildMutation,
  } = usePlatformDeploymentEditor({
    mode: "create",
    capabilities,
    providers,
    eligibleModelsByCapability,
    t,
  });
  const [form, setForm] = useState<DeploymentFormState>(() => buildInitialForm());
  const [errorMessage, setErrorMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    const { validationError, mutationInput } = validateAndBuildMutation(form);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }
    if (!mutationInput) {
      return;
    }

    setSaving(true);
    setErrorMessage("");
    try {
      const deployment = await createDeploymentProfile(mutationInput, token);
      navigate(`/control/platform/deployments/${deployment.id}`, {
        state: { feedbackMessage: t("platformControl.feedback.deploymentCreated", { name: deployment.display_name }) },
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <PlatformPageLayout
      title={t("platformControl.deployments.newTitle")}
      description={t("platformControl.deployments.newDescription")}
      errorMessage={errorMessage || loadErrorMessage}
    >
      <article className="panel card-stack">
        <PlatformDeploymentForm
          value={form}
          capabilities={requiredCapabilities}
          providersByCapability={providersByCapability}
          modelResourcesByCapability={modelResourcesByCapability}
          helperText={t("platformControl.deployments.createHelp")}
          isSubmitting={saving}
          submitLabel={t("platformControl.actions.createDeployment")}
          submitBusyLabel={t("platformControl.actions.saving")}
          onChange={setForm}
          onSubmit={(event) => void handleSubmit(event)}
        />
      </article>
    </PlatformPageLayout>
  );
}
