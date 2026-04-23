import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeBase } from "../../../api/context";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformDeploymentBinding, PlatformProvider } from "../../../api/platform";
import {
  addCapabilityToDeploymentForm,
  getAvailableDeploymentCapabilities,
  getVisibleDeploymentCapabilities,
  type DeploymentFormState,
} from "../deploymentEditor";
import { buildDeploymentCapabilitySectionState } from "../deploymentFormSections";
import { capabilityRequiresModelResource } from "../capabilities";
import { filterModelsForProviderOrigin } from "../deploymentModelCompatibility";
import PlatformDeploymentCapabilitySection from "./PlatformDeploymentCapabilitySection";

type PlatformDeploymentFormProps = {
  value: DeploymentFormState;
  capabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  knowledgeBases: KnowledgeBase[];
  helperText: string;
  bindingStatusByCapability?: Record<string, PlatformDeploymentBinding["configuration_status"] | undefined>;
  identityAction?: {
    label: string;
    busyLabel: string;
    isSubmitting: boolean;
    onClick: () => void;
  };
  capabilityAction?: {
    label: string;
    busyLabel: string;
    savingByCapability: Record<string, boolean>;
    onClick: (capability: string) => void;
  };
  isSubmitting?: boolean;
  submitLabel?: string;
  submitBusyLabel?: string;
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  onChange: (value: DeploymentFormState) => void;
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
};

export default function PlatformDeploymentForm({
  value,
  capabilities,
  providersByCapability,
  modelResourcesByCapability,
  knowledgeBases,
  helperText,
  bindingStatusByCapability = {},
  identityAction,
  capabilityAction,
  isSubmitting,
  submitLabel,
  submitBusyLabel,
  secondaryAction,
  onChange,
  onSubmit,
}: PlatformDeploymentFormProps): JSX.Element {
  const { t } = useTranslation("common");
  const visibleCapabilities = getVisibleDeploymentCapabilities(capabilities, value);
  const availableCapabilities = getAvailableDeploymentCapabilities(capabilities, value);
  const [capabilityToAdd, setCapabilityToAdd] = useState("");

  useEffect(() => {
    if (availableCapabilities.length === 0) {
      if (capabilityToAdd) {
        setCapabilityToAdd("");
      }
      return;
    }
    if (!capabilityToAdd || !availableCapabilities.some((capability) => capability.capability === capabilityToAdd)) {
      setCapabilityToAdd(availableCapabilities[0]?.capability ?? "");
    }
  }, [availableCapabilities, capabilityToAdd]);

  const updateCapabilityProvider = (capability: string, providerId: string): void => {
    const nextProvider = (providersByCapability[capability] ?? []).find((provider) => provider.id === providerId) ?? null;
    const compatibleModelIds = new Set(
      filterModelsForProviderOrigin(modelResourcesByCapability[capability] ?? [], nextProvider).map((model) => model.id),
    );
    const previousResourceIds = value.resourceIdsByCapability[capability] ?? [];
    const nextResourceIds = capabilityRequiresModelResource(capability)
      ? previousResourceIds.filter((resourceId) => compatibleModelIds.has(resourceId))
      : previousResourceIds;
    const previousDefault = value.defaultResourceIdsByCapability[capability] ?? "";
    const nextDefault = nextResourceIds.includes(previousDefault) ? previousDefault : (nextResourceIds[0] ?? "");
    onChange({
      ...value,
      providerIdsByCapability: {
        ...value.providerIdsByCapability,
        [capability]: providerId,
      },
      resourceIdsByCapability: {
        ...value.resourceIdsByCapability,
        [capability]: nextResourceIds,
      },
      defaultResourceIdsByCapability: {
        ...value.defaultResourceIdsByCapability,
        [capability]: nextDefault,
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

  const updateCapabilityDefaultResource = (capability: string, resourceId: string): void => {
    onChange({
      ...value,
      defaultResourceIdsByCapability: {
        ...value.defaultResourceIdsByCapability,
        [capability]: resourceId,
      },
    });
  };

  const updateVectorSelectionMode = (capability: string, selectionMode: string): void => {
    onChange({
      ...value,
      resourcePolicyByCapability: {
        ...value.resourcePolicyByCapability,
        [capability]: {
          ...value.resourcePolicyByCapability[capability],
          selection_mode: selectionMode,
        },
      },
    });
  };

  const updateVectorNamespacePrefix = (capability: string, namespacePrefix: string): void => {
    onChange({
      ...value,
      resourcePolicyByCapability: {
        ...value.resourcePolicyByCapability,
        [capability]: {
          ...value.resourcePolicyByCapability[capability],
          selection_mode: "dynamic_namespace",
          namespace_prefix: namespacePrefix,
        },
      },
    });
  };

  return (
    <form className="card-stack" onSubmit={onSubmit}>
      <div className="deployment-settings-layout">
        <div className="deployment-identity-row panel panel-nested" data-testid="deployment-identity-row">
          <div className="deployment-binding-heading">
            <span className="field-label">{t("platformControl.forms.deployment.deploymentIdentity")}</span>
            <h4 className="deployment-binding-title">{t("platformControl.sections.settings")}</h4>
            <p className="status-text">{t("platformControl.deployments.settingsDescription")}</p>
            {identityAction ? (
              <div className="inline-meta-list">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={identityAction.onClick}
                  disabled={identityAction.isSubmitting}
                >
                  {identityAction.isSubmitting ? identityAction.busyLabel : identityAction.label}
                </button>
              </div>
            ) : null}
          </div>
          <label className="card-stack deployment-binding-field">
            <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
            <input
              className="field-input"
              value={value.slug}
              onChange={(event) => onChange({ ...value, slug: event.target.value })}
            />
          </label>
          <label className="card-stack deployment-binding-field">
            <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
            <input
              className="field-input"
              value={value.displayName}
              onChange={(event) => onChange({ ...value, displayName: event.target.value })}
            />
          </label>
        </div>

        {availableCapabilities.length > 0 ? (
          <div className="deployment-binding-row panel panel-nested" data-testid="deployment-add-capability-row">
            <div className="deployment-binding-heading">
              <span className="field-label">{t("platformControl.forms.deployment.binding")}</span>
              <h4 className="deployment-binding-title">{t("platformControl.forms.deployment.addCapabilityTitle")}</h4>
              <p className="status-text">{t("platformControl.deployments.addCapabilityDescription")}</p>
            </div>
            <label className="card-stack deployment-binding-field">
              <span className="field-label">{t("platformControl.forms.deployment.capability")}</span>
              <select
                className="field-input"
                value={capabilityToAdd}
                onChange={(event) => setCapabilityToAdd(event.target.value)}
              >
                {availableCapabilities.map((capability) => (
                  <option key={capability.capability} value={capability.capability}>
                    {capability.display_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="inline-meta-list">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!capabilityToAdd}
                onClick={() => {
                  if (!capabilityToAdd) {
                    return;
                  }
                  onChange(addCapabilityToDeploymentForm(value, capabilityToAdd));
                }}
              >
                {t("platformControl.actions.addCapability")}
              </button>
            </div>
          </div>
        ) : null}

        {visibleCapabilities.map((capability) => {
          const section = buildDeploymentCapabilitySectionState({
            capability,
            value,
            providersByCapability,
            modelResourcesByCapability,
            knowledgeBases,
            bindingStatusByCapability,
            t,
          });

          return (
            <PlatformDeploymentCapabilitySection
              key={section.capabilityKey}
              section={section}
              onProviderChange={(providerId) => updateCapabilityProvider(section.capabilityKey, providerId)}
              onResourceChange={(resourceIds) => updateCapabilityResources(section.capabilityKey, resourceIds)}
              onDefaultResourceChange={(resourceId) => updateCapabilityDefaultResource(section.capabilityKey, resourceId)}
              onVectorSelectionModeChange={(selectionMode) => updateVectorSelectionMode(section.capabilityKey, selectionMode)}
              onNamespacePrefixChange={(namespacePrefix) => updateVectorNamespacePrefix(section.capabilityKey, namespacePrefix)}
              saveAction={capabilityAction ? {
                label: capabilityAction.label,
                busyLabel: capabilityAction.busyLabel,
                isSaving: Boolean(capabilityAction.savingByCapability[section.capabilityKey]),
                onSave: () => capabilityAction.onClick(section.capabilityKey),
              } : undefined}
            />
          );
        })}
      </div>
      <label className="card-stack">
        <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
        <textarea
          className="field-input form-textarea"
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
          {submitLabel && submitBusyLabel && onSubmit ? (
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? submitBusyLabel : submitLabel}
            </button>
          ) : null}
        </div>
      </div>
    </form>
  );
}
