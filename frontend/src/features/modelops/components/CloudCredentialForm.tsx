import { useTranslation } from "react-i18next";

type CredentialFormState = {
  provider: string;
  credentialScope: "platform" | "personal";
  displayName: string;
  apiBaseUrl: string;
  apiKey: string;
};

type CloudCredentialFormProps = {
  state: CredentialFormState;
  isSaving: boolean;
  canChoosePlatformScope: boolean;
  onChange: (next: CredentialFormState) => void;
  onSubmit: () => Promise<void>;
};

export default function CloudCredentialForm({
  state,
  isSaving,
  canChoosePlatformScope,
  onChange,
  onSubmit,
}: CloudCredentialFormProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.cloud.credentialsTitle")}</h2>
      <div className="control-group">
        <label className="field-label" htmlFor="cloud-credential-provider">{t("modelOps.fields.provider")}</label>
        <select
          id="cloud-credential-provider"
          className="field-input"
          value={state.provider}
          onChange={(event) => onChange({ ...state, provider: event.currentTarget.value })}
        >
          <option value="openai_compatible">OpenAI-compatible</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
        </select>
        {canChoosePlatformScope && (
          <>
            <label className="field-label" htmlFor="cloud-credential-scope">{t("modelOps.fields.credentialScope")}</label>
            <select
              id="cloud-credential-scope"
              className="field-input"
              value={state.credentialScope}
              onChange={(event) => onChange({ ...state, credentialScope: event.currentTarget.value as "platform" | "personal" })}
            >
              <option value="personal">{t("modelOps.scopes.personal")}</option>
              <option value="platform">{t("modelOps.scopes.platform")}</option>
            </select>
          </>
        )}
        <label className="field-label" htmlFor="cloud-credential-display-name">{t("modelOps.fields.displayName")}</label>
        <input
          id="cloud-credential-display-name"
          className="field-input"
          value={state.displayName}
          onChange={(event) => onChange({ ...state, displayName: event.currentTarget.value })}
        />
        <label className="field-label" htmlFor="cloud-credential-base-url">{t("modelOps.fields.apiBaseUrl")}</label>
        <input
          id="cloud-credential-base-url"
          className="field-input"
          value={state.apiBaseUrl}
          onChange={(event) => onChange({ ...state, apiBaseUrl: event.currentTarget.value })}
        />
        <label className="field-label" htmlFor="cloud-credential-api-key">{t("modelOps.fields.apiKey")}</label>
        <input
          id="cloud-credential-api-key"
          type="password"
          className="field-input"
          value={state.apiKey}
          onChange={(event) => onChange({ ...state, apiKey: event.currentTarget.value })}
        />
        <button type="button" className="btn btn-primary" disabled={isSaving} onClick={() => void onSubmit()}>
          {t("modelOps.actions.saveCredential")}
        </button>
      </div>
    </article>
  );
}
