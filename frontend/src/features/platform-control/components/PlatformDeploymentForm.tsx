import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../../api/platform";
import type { DeploymentFormState } from "../utils";

type PlatformDeploymentFormProps = {
  value: DeploymentFormState;
  capabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
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

function requiresModelResources(capability: string): boolean {
  return capability === "llm_inference" || capability === "embeddings";
}

function supportsVectorResources(capability: string): boolean {
  return capability === "vector_store";
}

export default function PlatformDeploymentForm({
  value,
  capabilities,
  providersByCapability,
  modelResourcesByCapability,
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

  const updateCapabilityResources = (capability: string, resourceIds: string[]): void => {
    const previousDefault = value.defaultResourceIdsByCapability[capability] ?? "";
    const nextDefault = resourceIds.includes(previousDefault) ? previousDefault : (resourceIds[0] ?? "");
    onChange({
      ...value,
      resourceIdsByCapability: {
        ...value.resourceIdsByCapability,
        [capability]: resourceIds,
      },
      defaultResourceIdsByCapability: {
        ...value.defaultResourceIdsByCapability,
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
        {capabilities.map((capability) => {
          const capabilityKey = capability.capability;
          const capabilityProviders = providersByCapability[capabilityKey] ?? [];
          const selectedProviderId = value.providerIdsByCapability[capabilityKey] ?? "";
          const selectedProvider = capabilityProviders.find((provider) => provider.id === selectedProviderId) ?? null;
          const modelOptions = modelResourcesByCapability[capabilityKey] ?? [];
          const selectedResourceIds = value.resourceIdsByCapability[capabilityKey] ?? [];
          const availableDefaultResources = modelOptions.filter((model) => selectedResourceIds.includes(model.id));
          const loadedManagedModelId = selectedProvider?.loaded_managed_model_id ?? null;
          const loadedManagedModelName = selectedProvider?.loaded_managed_model_name ?? loadedManagedModelId ?? "";
          const loadedModelIsEligible = loadedManagedModelId
            ? modelOptions.some((model) => model.id === loadedManagedModelId)
            : false;
          const showLoadedModelEligibilityHint = requiresModelResources(capabilityKey)
            && modelOptions.length === 0
            && Boolean(loadedManagedModelId)
            && !loadedModelIsEligible;
          const showGenericEmptyHint = requiresModelResources(capabilityKey)
            && modelOptions.length === 0
            && !showLoadedModelEligibilityHint;

          return (
            <div key={capabilityKey} className="card-stack">
              <label className="card-stack">
                <span className="field-label">
                  {t("platformControl.forms.deployment.providerForCapability", {
                    capability: capability.display_name,
                  })}
                </span>
                <select
                  className="field-input"
                  value={selectedProviderId}
                  onChange={(event) => updateCapabilityProvider(capabilityKey, event.target.value)}
                >
                  <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                  {capabilityProviders.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {requiresModelResources(capabilityKey) ? (
                <>
                  <label className="card-stack">
                    <span className="field-label">
                      {t("platformControl.forms.deployment.resourcesForCapability", {
                        capability: capability.display_name,
                      })}
                    </span>
                    <select
                      className="field-input"
                      multiple
                      value={selectedResourceIds}
                      onChange={(event) =>
                        updateCapabilityResources(
                          capabilityKey,
                          Array.from(event.target.selectedOptions, (option) => option.value),
                        )
                      }
                    >
                      {modelOptions.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {showLoadedModelEligibilityHint ? (
                    <p className="status-text">
                      {t("platformControl.forms.deployment.loadedModelNotEligibleHint", {
                        capability: capability.display_name,
                        provider: selectedProvider?.display_name ?? t("platformControl.summary.none"),
                        model: loadedManagedModelName,
                      })}
                    </p>
                  ) : null}
                  {showGenericEmptyHint ? (
                    <p className="status-text">
                      {t("platformControl.forms.deployment.noEligibleResourcesHint", {
                        capability: capability.display_name,
                      })}
                    </p>
                  ) : null}
                  <label className="card-stack">
                    <span className="field-label">
                      {t("platformControl.forms.deployment.defaultResourceForCapability", {
                        capability: capability.display_name,
                      })}
                    </span>
                    <select
                      className="field-input"
                      value={value.defaultResourceIdsByCapability[capabilityKey] ?? ""}
                      disabled={modelOptions.length === 0}
                      onChange={(event) =>
                        onChange({
                          ...value,
                          defaultResourceIdsByCapability: {
                            ...value.defaultResourceIdsByCapability,
                            [capabilityKey]: event.target.value,
                          },
                        })
                      }
                    >
                      <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
                      {availableDefaultResources.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              ) : supportsVectorResources(capabilityKey) ? (
              <>
                <label className="card-stack">
                  <span className="field-label">{t("platformControl.forms.deployment.vectorSelectionMode")}</span>
                  <select
                    className="field-input"
                    value={String(value.resourcePolicyByCapability[capabilityKey]?.selection_mode ?? "explicit")}
                    onChange={(event) =>
                      onChange({
                        ...value,
                        resourcePolicyByCapability: {
                          ...value.resourcePolicyByCapability,
                          [capabilityKey]: {
                            ...value.resourcePolicyByCapability[capabilityKey],
                            selection_mode: event.target.value,
                          },
                        },
                      })
                    }
                  >
                    <option value="explicit">Explicit resources</option>
                    <option value="dynamic_namespace">Dynamic namespace</option>
                  </select>
                </label>
                {String(value.resourcePolicyByCapability[capabilityKey]?.selection_mode ?? "explicit") === "dynamic_namespace" ? (
                  <label className="card-stack">
                    <span className="field-label">{t("platformControl.forms.deployment.namespacePrefix")}</span>
                    <input
                      className="field-input"
                      value={String(value.resourcePolicyByCapability[capabilityKey]?.namespace_prefix ?? "")}
                      onChange={(event) =>
                        onChange({
                          ...value,
                          resourcePolicyByCapability: {
                            ...value.resourcePolicyByCapability,
                            [capabilityKey]: {
                              ...value.resourcePolicyByCapability[capabilityKey],
                              selection_mode: "dynamic_namespace",
                              namespace_prefix: event.target.value,
                            },
                          },
                        })
                      }
                    />
                  </label>
                ) : (
                  <label className="card-stack">
                    <span className="field-label">{t("platformControl.forms.deployment.explicitResources")}</span>
                    <textarea
                      className="field-input quote-admin-textarea"
                      value={selectedResourceIds.join("\n")}
                      onChange={(event) =>
                        updateCapabilityResources(
                          capabilityKey,
                          event.target.value
                            .split("\n")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        )
                      }
                    />
                  </label>
                )}
              </>
              ) : null}
            </div>
          );
        })}
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
