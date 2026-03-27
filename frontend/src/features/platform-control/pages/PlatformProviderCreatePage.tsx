import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createPlatformProvider } from "../../../api/platform";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import PlatformPageLayout from "../components/PlatformPageLayout";
import PlatformProviderForm from "../components/PlatformProviderForm";
import { usePlatformProvidersData } from "../hooks/usePlatformProvidersData";
import { DEFAULT_PROVIDER_FORM, parseJsonObject } from "../providerForm";

export default function PlatformProviderCreatePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const navigate = useNavigate();
  const { showErrorFeedback } = useActionFeedback();
  const { errorMessage: loadErrorMessage, providerFamilies } = usePlatformProvidersData(token);
  const [form, setForm] = useState(DEFAULT_PROVIDER_FORM);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    setSaving(true);
    try {
      const config = parseJsonObject(
        form.configText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.config") }),
      );
      const secretRefs = parseJsonObject(
        form.secretRefsText,
        t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.secretRefs") }),
      ) as Record<string, string>;
      const provider = await createPlatformProvider(
        {
          provider_key: form.providerKey,
          slug: form.slug,
          display_name: form.displayName,
          description: form.description,
          endpoint_url: form.endpointUrl,
          healthcheck_url: form.healthcheckUrl || null,
          enabled: form.enabled,
          config,
          secret_refs: secretRefs,
        },
        token,
      );
      navigate(`/control/platform/providers/${provider.id}`, {
        state: withActionFeedbackState({
          kind: "success",
          message: t("platformControl.feedback.providerCreated", { name: provider.display_name }),
        }),
      });
    } catch (error) {
      showErrorFeedback(error, t("platformControl.feedback.providerSaveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <PlatformPageLayout
      title={t("platformControl.providers.newTitle")}
      description={t("platformControl.providers.newDescription")}
      errorMessage={loadErrorMessage}
    >
      <article className="panel card-stack">
        <PlatformProviderForm
          value={form}
          providerFamilies={providerFamilies}
          helperText={t("platformControl.providers.createHelp")}
          isSubmitting={saving}
          submitLabel={t("platformControl.actions.createProvider")}
          submitBusyLabel={t("platformControl.actions.saving")}
          onChange={setForm}
          onSubmit={(event) => void handleSubmit(event)}
        />
      </article>
    </PlatformPageLayout>
  );
}
