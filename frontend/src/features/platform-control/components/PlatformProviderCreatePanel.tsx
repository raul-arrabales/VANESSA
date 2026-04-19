import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createPlatformProvider } from "../../../api/platform";
import { listModelCredentials } from "../../../api/modelops/credentials";
import type { ModelCredential } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { usePlatformProvidersData } from "../hooks/usePlatformProvidersData";
import { DEFAULT_PROVIDER_FORM, normalizeOptionalUrl, parseJsonObject, updateSecretRefsCredential } from "../providerForm";
import PlatformProviderForm from "./PlatformProviderForm";

export default function PlatformProviderCreatePanel(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const navigate = useNavigate();
  const { showErrorFeedback } = useActionFeedback();
  const { errorMessage: loadErrorMessage, providerFamilies } = usePlatformProvidersData(token);
  const [form, setForm] = useState(DEFAULT_PROVIDER_FORM);
  const [saving, setSaving] = useState(false);
  const [credentials, setCredentials] = useState<ModelCredential[]>([]);
  const [credentialsLoading, setCredentialsLoading] = useState(false);
  const selectedFamily = providerFamilies.find((family) => family.provider_key === form.providerKey) ?? null;
  const supportsSavedCredentials = selectedFamily
    ? selectedFamily.provider_key === "openai_compatible_cloud_llm"
      || selectedFamily.provider_key === "openai_compatible_cloud_embeddings"
    : false;
  const providerCredentials = useMemo(
    () => credentials.filter((credential) => credential.provider === "openai" || credential.provider === "openai_compatible"),
    [credentials],
  );

  useEffect(() => {
    if (!token || !supportsSavedCredentials) {
      setCredentials([]);
      setCredentialsLoading(false);
      return;
    }
    let isActive = true;
    setCredentialsLoading(true);
    void listModelCredentials(token)
      .then((rows) => {
        if (isActive) {
          setCredentials(rows);
        }
      })
      .catch(() => {
        if (isActive) {
          setCredentials([]);
        }
      })
      .finally(() => {
        if (isActive) {
          setCredentialsLoading(false);
        }
      });
    return () => {
      isActive = false;
    };
  }, [supportsSavedCredentials, token]);

  useEffect(() => {
    if (supportsSavedCredentials || !form.credentialId) {
      return;
    }
    setForm((current) => ({
      ...current,
      credentialId: "",
      secretRefsText: updateSecretRefsCredential(current.secretRefsText, ""),
    }));
  }, [form.credentialId, supportsSavedCredentials]);

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
          healthcheck_url: normalizeOptionalUrl(form.healthcheckUrl),
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
    <>
      {loadErrorMessage ? <p className="status-text error-text">{`${t("platformControl.feedback.prefix")} ${loadErrorMessage}`}</p> : null}
      <article className="panel card-stack">
        <PlatformProviderForm
          value={form}
          providerFamilies={providerFamilies}
          helperText={t("platformControl.providers.createHelp")}
          isSubmitting={saving}
          submitLabel={t("platformControl.actions.createProvider")}
          submitBusyLabel={t("platformControl.actions.saving")}
          credentials={providerCredentials}
          credentialsLoading={credentialsLoading}
          supportsSavedCredentials={supportsSavedCredentials}
          onChange={setForm}
          onSubmit={(event) => void handleSubmit(event)}
        />
      </article>
    </>
  );
}
