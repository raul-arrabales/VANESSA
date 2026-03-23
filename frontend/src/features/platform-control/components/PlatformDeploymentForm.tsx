import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../../api/platform";
import type { DeploymentFormState } from "../utils";

type PlatformDeploymentFormProps = {
  value: DeploymentFormState;
  capabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  servedModelsByCapability: Record<string, ManagedModel[]>;
  helperText: string;
  isSubmitting: boolean;
  submitLabel: string;
  submitBusyLabel: string;
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  onChange: (value: DeploymentFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function requiresServedModels(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
}

export default function PlatformDeploymentForm({
  value,
  capabilities,
  providersByCapability,
  servedModelsByCapability,
  helperText,
  isSubmitting,
  submitLabel,
  submitBusyLabel,
  secondaryAction,
  onChange,
  onSubmit,
}: PlatformDeploymentFormProps): JSX.Element {
  const { t } = useTranslation("common");

  const updateCapabilityProvider = (capability: string, providerId: string): void => {
    onChange({
      ...value,
      providerIdsByCapability: {
        ...value.providerIdsByCapability,
        [capability]: providerId,
      },
    });
  };

  const updateCapabilityServedModels = (capability: string, servedModelIds: string[]): void => {
    const previousDefault = value.defaultServedModelIdsByCapability[capability] ?? "";
    const nextDefault = servedModelIds.includes(previousDefault) ? previousDefault : (servedModelIds[0] ?? "");
    onChange({
      ...value,
      servedModelIdsByCapability: {
        ...value.servedModelIdsByCapability,
        [capability]: servedModelIds,
      },
      defaultServedModelIdsByCapability: {
        ...value.defaultServedModelIdsByCapability,
        [capability]: nextDefault,
      },
    });
  };

  return (
    <form className="card-stack" onSubmit={onSubmit}>
      <div className="form-grid">
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
          <input
            className="field-input"
            value={value.slug}
            onChange={(event) => onChange({ ...value, slug: event.target.value })}
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
          <input
            className="field-input"
            value={value.displayName}
            onChange={(event) => onChange({ ...value, displayName: event.target.value })}
          />
        </label>
        {capabilities.map((capability) => (
          <div key={capability.capability} className="card-stack">
            <label className="card-stack">
              <span className="field-label">
                {t("platformControl.forms.deployment.providerForCapability", {
                  capability: capability.display_name,
                })}
              </span>
              <select
                className="field-input"
                value={value.providerIdsByCapability[capability.capability] ?? ""}
                onChange={(event) => updateCapabilityProvider(capability.capability, event.target.value)}
              >
                <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                {(providersByCapability[capability.capability] ?? []).map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.display_name}
                  </option>
                ))}
              </select>
            </label>
            {requiresServedModels(capability.capability) ? (
              <>
                <label className="card-stack">
                  <span className="field-label">
                    {t("platformControl.forms.deployment.servedModelsForCapability", {
                      capability: capability.display_name,
                    })}
                  </span>
                  <select
                    className="field-input"
                    multiple
                    value={value.servedModelIdsByCapability[capability.capability] ?? []}
                    onChange={(event) =>
                      updateCapabilityServedModels(
                        capability.capability,
                        Array.from(event.target.selectedOptions, (option) => option.value),
                      )
                    }
                  >
                    {(servedModelsByCapability[capability.capability] ?? []).map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">
                    {t("platformControl.forms.deployment.defaultServedModelForCapability", {
                      capability: capability.display_name,
                    })}
                  </span>
                  <select
                    className="field-input"
                    value={value.defaultServedModelIdsByCapability[capability.capability] ?? ""}
                    onChange={(event) =>
                      onChange({
                        ...value,
                        defaultServedModelIdsByCapability: {
                          ...value.defaultServedModelIdsByCapability,
                          [capability.capability]: event.target.value,
                        },
                      })
                    }
                  >
                    <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                    {(servedModelsByCapability[capability.capability] ?? [])
                      .filter((model) => (value.servedModelIdsByCapability[capability.capability] ?? []).includes(model.id))
                      .map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name}
                        </option>
                      ))}
                  </select>
                </label>
              </>
            ) : null}
          </div>
        ))}
      </div>
      <label className="card-stack">
        <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
        <textarea
          className="field-input quote-admin-textarea"
          value={value.description}
          onChange={(event) => onChange({ ...value, description: event.target.value })}
        />
      </label>
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
