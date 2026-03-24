import { type FormEvent, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createDeploymentProfile } from "../api/platform";
import { useAuth } from "../auth/AuthProvider";
import PlatformDeploymentForm from "../features/platform-control/components/PlatformDeploymentForm";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import { usePlatformDeploymentEditorData } from "../features/platform-control/hooks/usePlatformDeploymentEditorData";
import {
  buildDeploymentMutationInput,
  DEFAULT_DEPLOYMENT_FORM,
  getCapabilityProviders,
  getManagedModelsByCapability,
  validateDeploymentForm,
} from "../features/platform-control/utils";

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
  const [form, setForm] = useState(DEFAULT_DEPLOYMENT_FORM);
  const [errorMessage, setErrorMessage] = useState("");
  const [saving, setSaving] = useState(false);

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    const validationError = validateDeploymentForm(requiredCapabilities, form, {
      bindingRequiredMessage: t("platformControl.feedback.bindingRequired"),
      resourceRequiredMessage: (capabilityDisplayName) =>
        t("platformControl.feedback.resourceRequired", { capability: capabilityDisplayName }),
      defaultResourceRequiredMessage: (capabilityDisplayName) =>
        t("platformControl.feedback.defaultResourceRequired", { capability: capabilityDisplayName }),
    });
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setSaving(true);
    setErrorMessage("");
    try {
      const deployment = await createDeploymentProfile(
        buildDeploymentMutationInput(requiredCapabilities, form),
        token,
      );
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
