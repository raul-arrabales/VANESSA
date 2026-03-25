import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops";
import type { PlatformCapability, PlatformProvider } from "../../../api/platform";
import { buildDeploymentCapabilitySectionState } from "../deploymentFormSections";
import type { DeploymentFormState } from "../utils";
import PlatformDeploymentCapabilitySection from "./PlatformDeploymentCapabilitySection";

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
          const section = buildDeploymentCapabilitySectionState({
            capability,
            value,
            providersByCapability,
            modelResourcesByCapability,
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
            />
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
