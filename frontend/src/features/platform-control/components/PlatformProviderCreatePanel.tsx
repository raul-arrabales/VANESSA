import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createPlatformProvider } from "../../../api/platform";
import { listModelCredentials } from "../../../api/modelops/credentials";
import type { ModelCredential } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../../../feedback/ActionFeedbackProvider";
import { usePlatformProvidersData } from "../hooks/usePlatformProvidersData";
import {
  buildProviderMutationInput,
  DEFAULT_PROVIDER_FORM,
  supportsSavedCredentials,
  updateSecretRefsCredential,
} from "../providerForm";
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
  const providerSupportsSavedCredentials = supportsSavedCredentials(form.providerKey);
  const providerCredentials = useMemo(
    () => credentials.filter((credential) => credential.provider === "openai" || credential.provider === "openai_compatible"),
    [credentials],
  );

  useEffect(() => {
    if (!token || !providerSupportsSavedCredentials) {
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
  }, [providerSupportsSavedCredentials, token]);

  useEffect(() => {
    if (providerSupportsSavedCredentials || !form.credentialId) {
      return;
    }
    setForm((current) => ({
      ...current,
      credentialId: "",
      secretRefsText: updateSecretRefsCredential(current.secretRefsText, ""),
    }));
  }, [form.credentialId, providerSupportsSavedCredentials]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }

    setSaving(true);
    try {
      const provider = await createPlatformProvider(
        buildProviderMutationInput(form, {
          configErrorMessage: t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.config") }),
          secretRefsErrorMessage: t("platformControl.feedback.invalidJson", { field: t("platformControl.forms.provider.secretRefs") }),
        }),
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
          supportsSavedCredentials={providerSupportsSavedCredentials}
          onChange={setForm}
          onSubmit={(event) => void handleSubmit(event)}
        />
      </article>
    </>
  );
}
