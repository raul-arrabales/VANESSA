import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { ModelCredential } from "../../../api/modelops/types";
import { TASK_OPTIONS } from "../domain";

type CloudModelRegistrationState = {
  id: string;
  name: string;
  provider: string;
  ownerType: "platform" | "user";
  visibilityScope: "private" | "user" | "group" | "platform";
  providerModelId: string;
  credentialId: string;
  taskKey: string;
  comment: string;
};

type CloudModelRegistrationFormProps = {
  state: CloudModelRegistrationState;
  credentials: ModelCredential[];
  isSaving: boolean;
  allowPlatformOwnership: boolean;
  onChange: (next: CloudModelRegistrationState) => void;
  onSubmit: () => Promise<void>;
};

export default function CloudModelRegistrationForm({
  state,
  credentials,
  isSaving,
  allowPlatformOwnership,
  onChange,
  onSubmit,
}: CloudModelRegistrationFormProps): JSX.Element {
  const { t } = useTranslation("common");

  const filteredCredentials = useMemo(
    () => credentials.filter((credential) => credential.provider === state.provider),
    [credentials, state.provider],
  );

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.cloud.registrationTitle")}</h2>
      <div className="control-group">
        <label className="field-label" htmlFor="cloud-model-id">{t("modelOps.fields.modelId")}</label>
        <input id="cloud-model-id" className="field-input" value={state.id} onChange={(event) => onChange({ ...state, id: event.currentTarget.value })} />
        <label className="field-label" htmlFor="cloud-model-name">{t("modelOps.fields.modelName")}</label>
        <input id="cloud-model-name" className="field-input" value={state.name} onChange={(event) => onChange({ ...state, name: event.currentTarget.value })} />
        <label className="field-label" htmlFor="cloud-model-provider">{t("modelOps.fields.provider")}</label>
        <select
          id="cloud-model-provider"
          className="field-input"
          value={state.provider}
          onChange={(event) => onChange({ ...state, provider: event.currentTarget.value, credentialId: "" })}
        >
          <option value="openai_compatible">OpenAI-compatible</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
        </select>
        {allowPlatformOwnership && (
          <>
            <label className="field-label" htmlFor="cloud-model-owner-type">{t("modelOps.fields.ownerType")}</label>
            <select
              id="cloud-model-owner-type"
              className="field-input"
              value={state.ownerType}
              onChange={(event) => onChange({ ...state, ownerType: event.currentTarget.value as "platform" | "user" })}
            >
              <option value="user">{t("modelOps.scopes.personal")}</option>
              <option value="platform">{t("modelOps.scopes.platform")}</option>
            </select>
            <label className="field-label" htmlFor="cloud-model-visibility">{t("modelOps.fields.visibilityScope")}</label>
            <select
              id="cloud-model-visibility"
              className="field-input"
              value={state.visibilityScope}
              onChange={(event) => onChange({ ...state, visibilityScope: event.currentTarget.value as "private" | "user" | "group" | "platform" })}
            >
              <option value="private">{t("modelOps.visibility.private")}</option>
              <option value="user">{t("modelOps.visibility.user")}</option>
              <option value="group">{t("modelOps.visibility.group")}</option>
              <option value="platform">{t("modelOps.visibility.platform")}</option>
            </select>
          </>
        )}
        <label className="field-label" htmlFor="cloud-provider-model-id">{t("modelOps.fields.providerModelId")}</label>
        <input
          id="cloud-provider-model-id"
          className="field-input"
          value={state.providerModelId}
          onChange={(event) => onChange({ ...state, providerModelId: event.currentTarget.value })}
        />
        <label className="field-label" htmlFor="cloud-credential-id">{t("modelOps.fields.credential")}</label>
        <select
          id="cloud-credential-id"
          className="field-input"
          value={state.credentialId}
          onChange={(event) => onChange({ ...state, credentialId: event.currentTarget.value })}
        >
          <option value="">{t("modelOps.cloud.selectCredential")}</option>
          {filteredCredentials.map((credential) => (
            <option key={credential.id} value={credential.id}>
              {`${credential.display_name} · ****${credential.api_key_last4}`}
            </option>
          ))}
        </select>
        <label className="field-label" htmlFor="cloud-model-task">{t("modelOps.fields.task")}</label>
        <select
          id="cloud-model-task"
          className="field-input"
          value={state.taskKey}
          onChange={(event) => onChange({ ...state, taskKey: event.currentTarget.value })}
        >
          {TASK_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <label className="field-label" htmlFor="cloud-model-comment">{t("modelOps.fields.comment")}</label>
        <input
          id="cloud-model-comment"
          className="field-input"
          value={state.comment}
          onChange={(event) => onChange({ ...state, comment: event.currentTarget.value })}
        />
        <button type="button" className="btn btn-primary" disabled={isSaving} onClick={() => void onSubmit()}>
          {t("modelOps.actions.registerCloud")}
        </button>
      </div>
    </article>
  );
}
