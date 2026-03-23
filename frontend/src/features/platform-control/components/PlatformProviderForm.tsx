import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { PlatformProviderFamily } from "../../../api/platform";
import type { ProviderFormState } from "../utils";

type PlatformProviderFormProps = {
  value: ProviderFormState;
  providerFamilies: PlatformProviderFamily[];
  familyDisabled?: boolean;
  helperText: string;
  isSubmitting: boolean;
  submitLabel: string;
  submitBusyLabel: string;
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
  helperText,
  isSubmitting,
  submitLabel,
  submitBusyLabel,
  secondaryAction,
  onChange,
  onSubmit,
}: PlatformProviderFormProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <form className="card-stack" onSubmit={onSubmit}>
      <div className="form-grid">
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.family")}</span>
          <select
            className="field-input"
            value={value.providerKey}
            disabled={familyDisabled}
            onChange={(event) => onChange({ ...value, providerKey: event.target.value })}
          >
            <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
            {providerFamilies.map((family) => (
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
      <label className="card-stack">
        <span className="field-label">{t("platformControl.forms.provider.description")}</span>
        <textarea
          className="field-input quote-admin-textarea"
          value={value.description}
          onChange={(event) => onChange({ ...value, description: event.target.value })}
        />
      </label>
      <div className="form-grid">
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.config")}</span>
          <textarea
            className="field-input quote-admin-textarea"
            value={value.configText}
            onChange={(event) => onChange({ ...value, configText: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.provider.secretRefs")}</span>
          <textarea
            className="field-input quote-admin-textarea"
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
