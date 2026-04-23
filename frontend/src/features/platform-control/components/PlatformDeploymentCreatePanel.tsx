import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createDeploymentProfile } from "../../../api/platform";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import type { DeploymentFormState } from "../deploymentEditor";
import { withDeploymentSeedState } from "../deploymentRouteState";
import { usePlatformDeploymentEditor } from "../hooks/usePlatformDeploymentEditor";
import { usePlatformDeploymentEditorData } from "../hooks/usePlatformDeploymentEditorData";
import PlatformDeploymentForm from "./PlatformDeploymentForm";

export default function PlatformDeploymentCreatePanel(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const navigate = useNavigate();
  const { showErrorFeedback } = useActionFeedback();
  const {
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    eligibleModelsByCapability,
    knowledgeBases,
  } = usePlatformDeploymentEditorData(token);
  const {
    capabilities: editorCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    validateAndBuildMutation,
  } = usePlatformDeploymentEditor({
    mode: "create",
    capabilities,
    providers,
    eligibleModelsByCapability,
    knowledgeBases,
    t,
  });
  const [form, setForm] = useState<DeploymentFormState>(() => buildInitialForm());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const nextInitialForm = buildInitialForm();
    const shouldHydrateRequiredCapabilities = form.capabilityKeys.length === 0
      && nextInitialForm.capabilityKeys.length > 0
      && !form.slug
      && !form.displayName
      && !form.description
      && Object.keys(form.providerIdsByCapability).length === 0;
    if (shouldHydrateRequiredCapabilities) {
      setForm(nextInitialForm);
    }
  }, [buildInitialForm, form]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    const { validationError, mutationInput } = validateAndBuildMutation(form);
    if (validationError) {
      showErrorFeedback(validationError, t("platformControl.feedback.deploymentSaveFailed"));
      return;
    }
    if (!mutationInput) {
      return;
    }

    setSaving(true);
    try {
      const deployment = await createDeploymentProfile(mutationInput, token);
      navigate(`/control/platform/deployments/${deployment.id}`, {
        state: withDeploymentSeedState(
          deployment,
          withActionFeedbackState({
            kind: "success",
            message: t("platformControl.feedback.deploymentCreated", { name: deployment.display_name }),
          }),
        ),
      });
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.deploymentSaveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {loadErrorMessage ? <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${loadErrorMessage}`}</p> : null}
      <article className="panel card-stack">
        <PlatformDeploymentForm
          value={form}
          capabilities={editorCapabilities}
          providersByCapability={providersByCapability}
          modelResourcesByCapability={modelResourcesByCapability}
          knowledgeBases={knowledgeBases}
          helperText={t("platformControl.deployments.createHelp")}
          isSubmitting={saving}
          submitLabel={t("platformControl.actions.createDeployment")}
          submitBusyLabel={t("platformControl.actions.saving")}
          onChange={setForm}
          onSubmit={(event) => void handleSubmit(event)}
        />
      </article>
    </>
  );
}
