import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { ModelCredential } from "../../../api/modelops/types";
import type { PlatformProviderFamily } from "../../../api/platform";
import {
  applyProviderFamilyDefaults,
  filterProviderFamiliesByOrigin,
  PROVIDER_ORIGIN_OPTIONS,
  updateSecretRefsCredential,
  type ProviderFormState,
  type ProviderOriginSelection,
} from "../providerForm";

type PlatformProviderFormProps = {
  value: ProviderFormState;
  providerFamilies: PlatformProviderFamily[];
  familyDisabled?: boolean;
  showOriginSelector?: boolean;
  selectedOrigin?: ProviderOriginSelection;
  onOriginChange?: (origin: ProviderOriginSelection) => void;
  helperText: string;
  isSubmitting: boolean;
  submitLabel: string;
  submitBusyLabel: string;
  credentials?: ModelCredential[];
  credentialsLoading?: boolean;
  supportsSavedCredentials?: boolean;
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  onChange: (value: ProviderFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export default function PlatformProviderForm({
  value,
  providerFamilies,
  familyDisabled = false,
  showOriginSelector = false,
  selectedOrigin = "",
  onOriginChange,
  helperText,
  isSubmitting,
  submitLabel,
  submitBusyLabel,
  credentials = [],
  credentialsLoading = false,
  supportsSavedCredentials = false,
  secondaryAction,
  onChange,
  onSubmit,
}: PlatformProviderFormProps): JSX.Element {
  const { t } = useTranslation("common");
  const visibleProviderFamilies = filterProviderFamiliesByOrigin(providerFamilies, showOriginSelector ? selectedOrigin : "");
  const isFamilySelectionDisabled = familyDisabled || (showOriginSelector && !selectedOrigin);

  function handleCredentialChange(credentialId: string): void {
    onChange({
      ...value,
      credentialId,
      secretRefsText: updateSecretRefsCredential(value.secretRefsText, credentialId),
    });
  }

  return (
    <form className="card-stack" onSubmit={onSubmit}>
      <div className="form-grid">
        {showOriginSelector ? (
          <label className="card-stack">
            <span className="field-label">{t("platformControl.forms.provider.origin")}</span>
            <select
              className="field-input"
              value={selectedOrigin}
              onChange={(event) => onOriginChange?.((event.target.value as ProviderOriginSelection) || "")}
            >
              <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
              {PROVIDER_ORIGIN_OPTIONS.map((origin) => (
                <option key={origin.value} value={origin.value}>
                  {t(origin.labelKey)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.family")}</span>
          <select
            className="field-input"
            value={value.providerKey}
            disabled={isFamilySelectionDisabled}
            onChange={(event) => onChange(applyProviderFamilyDefaults(value, event.target.value))}
          >
            <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
            {visibleProviderFamilies.map((family) => (
              <option key={family.provider_key} value={family.provider_key}>
                {family.display_name}
              </option>
            ))}
          </select>
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.slug")}</span>
          <input
            className="field-input"
            value={value.slug}
            onChange={(event) => onChange({ ...value, slug: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.displayName")}</span>
          <input
            className="field-input"
            value={value.displayName}
            onChange={(event) => onChange({ ...value, displayName: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.endpoint")}</span>
          <input
            className="field-input"
            value={value.endpointUrl}
            onChange={(event) => onChange({ ...value, endpointUrl: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.healthcheck")}</span>
          <input
            className="field-input"
            value={value.healthcheckUrl}
            onChange={(event) => onChange({ ...value, healthcheckUrl: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.enabled")}</span>
          <select
            className="field-input"
            value={value.enabled ? "true" : "false"}
            onChange={(event) => onChange({ ...value, enabled: event.target.value === "true" })}
          >
            <option value="true">{t("platformControl.badges.enabled")}</option>
            <option value="false">{t("platformControl.badges.disabled")}</option>
          </select>
        </label>
      </div>
      {supportsSavedCredentials ? (
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.savedCredential")}</span>
          <select
            className="field-input"
            aria-label={t("platformControl.forms.provider.savedCredential")}
            value={value.credentialId}
            disabled={credentialsLoading}
            onChange={(event) => handleCredentialChange(event.target.value)}
          >
            <option value="">{t("platformControl.forms.provider.savedCredentialProviderSecrets")}</option>
            {credentials.map((credential) => (
              <option key={credential.id} value={credential.id}>
                {`${credential.display_name} · ${credential.provider} · saved ****${credential.api_key_last4}`}
              </option>
            ))}
          </select>
          <span className="status-text">
            {credentialsLoading
              ? t("platformControl.providers.validationCredentialsLoading")
              : credentials.length
                ? t("platformControl.forms.provider.savedCredentialHelp")
                : t("platformControl.providers.validationNoCredentials")}
          </span>
        </label>
      ) : null}
      <label className="card-stack">
        <span className="field-label">{t("platformControl.forms.provider.description")}</span>
        <textarea
          className="field-input form-textarea"
          value={value.description}
          onChange={(event) => onChange({ ...value, description: event.target.value })}
        />
      </label>
      <div className="form-grid">
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.config")}</span>
          <textarea
            className="field-input form-textarea"
            value={value.configText}
            onChange={(event) => onChange({ ...value, configText: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.secretRefs")}</span>
          <textarea
            className="field-input form-textarea"
            value={value.secretRefsText}
            onChange={(event) => onChange({ ...value, secretRefsText: event.target.value })}
          />
        </label>
      </div>
      <div className="platform-action-row">
        <span className="status-text">{helperText}</span>
        <div className="form-actions">
          {secondaryAction ? (
            <button type="button" className="btn btn-secondary" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </button>
          ) : null}
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? submitBusyLabel : submitLabel}
          </button>
        </div>
      </div>
    </form>
  );
}
