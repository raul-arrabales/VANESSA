import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/models";
import { useAuth } from "../../../auth/AuthProvider";
import ModelCatalogList from "../components/ModelCatalogList";
import CloudCredentialForm from "../components/CloudCredentialForm";
import CloudModelRegistrationForm from "../components/CloudModelRegistrationForm";
import { TASK_OPTIONS } from "../constants";
import { useCloudRegistrationFlow } from "../hooks/useCloudRegistrationFlow";

type CredentialFormState = {
  provider: string;
  credentialScope: "platform" | "personal";
  displayName: string;
  apiBaseUrl: string;
  apiKey: string;
};

type CloudModelState = {
  id: string;
  name: string;
  provider: string;
  ownerType: "platform" | "user";
  visibilityScope: "private" | "user" | "group" | "platform";
  providerModelId: string;
  credentialId: string;
  taskKey: string;
  comment: string;
  validateAfterRegister: boolean;
};

export default function CloudModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const { credentials, recentCloudModels, isLoading, isSaving, error, feedback, saveCredential, registerCloudModel } =
    useCloudRegistrationFlow(token);
  const isSuperadmin = user?.role === "superadmin";

  const [credentialState, setCredentialState] = useState<CredentialFormState>({
    provider: "openai_compatible",
    credentialScope: "personal" as const,
    displayName: "",
    apiBaseUrl: "https://api.openai.com/v1",
    apiKey: "",
  });

  const [modelState, setModelState] = useState<CloudModelState>({
    id: "",
    name: "",
    provider: "openai_compatible",
    ownerType: "user" as const,
    visibilityScope: "private" as const,
    providerModelId: "",
    credentialId: "",
    taskKey: "llm",
    comment: "",
    validateAfterRegister: true,
  });

  const recentModels = useMemo(
    () => recentCloudModels as ManagedModel[],
    [recentCloudModels],
  );

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.cloud.title")}</h2>
        <p className="status-text">
          {isSuperadmin ? t("modelOps.cloud.superadminDescription") : t("modelOps.cloud.description")}
        </p>
      </article>

      <CloudCredentialForm
        state={credentialState}
        isSaving={isSaving}
        canChoosePlatformScope={isSuperadmin}
        onChange={setCredentialState}
        onSubmit={async () => {
          await saveCredential({
            provider: credentialState.provider,
            display_name: credentialState.displayName.trim() || undefined,
            api_base_url: credentialState.apiBaseUrl.trim() || undefined,
            api_key: credentialState.apiKey,
            credential_scope: isSuperadmin ? credentialState.credentialScope : "personal",
          });
          setCredentialState((current) => ({ ...current, displayName: "", apiKey: "" }));
        }}
      />

      <CloudModelRegistrationForm
        state={modelState}
        credentials={credentials}
        isSaving={isSaving}
        allowPlatformOwnership={isSuperadmin}
        onChange={setModelState}
        onSubmit={async () => {
          const category = TASK_OPTIONS.find((option) => option.value === modelState.taskKey)?.category ?? "generative";
          await registerCloudModel({
            id: modelState.id.trim(),
            name: modelState.name.trim(),
            provider: modelState.provider,
            owner_type: isSuperadmin ? modelState.ownerType : "user",
            visibility_scope: isSuperadmin ? modelState.visibilityScope : "private",
            provider_model_id: modelState.providerModelId.trim(),
            credential_id: modelState.credentialId || undefined,
            task_key: modelState.taskKey,
            category,
            comment: modelState.comment.trim() || undefined,
            validate_after_register: modelState.validateAfterRegister,
          });
          setModelState({
            id: "",
            name: "",
            provider: modelState.provider,
            ownerType: "user",
            visibilityScope: "private",
            providerModelId: "",
            credentialId: "",
            taskKey: "llm",
            comment: "",
            validateAfterRegister: true,
          });
        }}
      />

      <article className="panel card-stack">
        <h2 className="section-title">{t("modelOps.cloud.recentTitle")}</h2>
        {isLoading ? (
          <p className="status-text">{t("modelOps.states.loading")}</p>
        ) : (
          <ModelCatalogList
            models={recentModels}
            emptyLabel={t("modelOps.cloud.emptyRecent")}
            detailLabel={t("modelOps.actions.openDetail")}
          />
        )}
      </article>

      {feedback && <p className="status-text">{feedback}</p>}
      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
