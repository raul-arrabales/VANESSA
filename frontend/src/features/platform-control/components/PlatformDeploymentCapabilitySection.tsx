import { useTranslation } from "react-i18next";
import type { DeploymentCapabilitySectionState } from "../deploymentFormSections";

type PlatformDeploymentCapabilitySectionProps = {
  section: DeploymentCapabilitySectionState;
  onProviderChange: (providerId: string) => void;
  onResourceChange: (resourceIds: string[]) => void;
  onDefaultResourceChange: (resourceId: string) => void;
  onVectorSelectionModeChange: (selectionMode: string) => void;
  onNamespacePrefixChange: (namespacePrefix: string) => void;
};

type ModelCapabilityFieldsProps = {
  section: DeploymentCapabilitySectionState;
  onResourceChange: (resourceIds: string[]) => void;
  onDefaultResourceChange: (resourceId: string) => void;
};

type VectorCapabilityFieldsProps = {
  section: DeploymentCapabilitySectionState;
  onResourceChange: (resourceIds: string[]) => void;
  onVectorSelectionModeChange: (selectionMode: string) => void;
  onNamespacePrefixChange: (namespacePrefix: string) => void;
};

function ModelCapabilityFields({
  section,
  onResourceChange,
  onDefaultResourceChange,
}: ModelCapabilityFieldsProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <label className="card-stack">
        <span className="field-label">
          {t("platformControl.forms.deployment.resourcesForCapability", {
            capability: section.capability.display_name,
          })}
        </span>
        <select
          className="field-input"
          multiple
          value={section.selectedResourceIds}
          onChange={(event) =>
            onResourceChange(Array.from(event.target.selectedOptions, (option) => option.value))
          }
        >
          {section.modelOptions.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name}
            </option>
          ))}
        </select>
      </label>
      {section.loadedModelEligibilityHint ? (
        <p className="status-text">{section.loadedModelEligibilityHint}</p>
      ) : null}
      {section.noEligibleResourcesHint ? (
        <p className="status-text">{section.noEligibleResourcesHint}</p>
      ) : null}
      <label className="card-stack">
        <span className="field-label">
          {t("platformControl.forms.deployment.defaultResourceForCapability", {
            capability: section.capability.display_name,
          })}
        </span>
        <select
          className="field-input"
          value={section.defaultResourceId}
          disabled={section.modelOptions.length === 0}
          onChange={(event) => onDefaultResourceChange(event.target.value)}
        >
          <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
          {section.availableDefaultResources.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

function VectorCapabilityFields({
  section,
  onResourceChange,
  onVectorSelectionModeChange,
  onNamespacePrefixChange,
}: VectorCapabilityFieldsProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <label className="card-stack">
        <span className="field-label">{t("platformControl.forms.deployment.vectorSelectionMode")}</span>
        <select
          className="field-input"
          value={section.vectorSelectionMode}
          onChange={(event) => onVectorSelectionModeChange(event.target.value)}
        >
          <option value="explicit">Explicit resources</option>
          <option value="dynamic_namespace">Dynamic namespace</option>
        </select>
      </label>
      {section.vectorSelectionMode === "dynamic_namespace" ? (
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.namespacePrefix")}</span>
          <input
            className="field-input"
            value={section.namespacePrefix}
            onChange={(event) => onNamespacePrefixChange(event.target.value)}
          />
        </label>
      ) : (
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.explicitResources")}</span>
          <textarea
            className="field-input quote-admin-textarea"
            value={section.selectedResourceIds.join("\n")}
            onChange={(event) =>
              onResourceChange(
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
  );
}

export default function PlatformDeploymentCapabilitySection({
  section,
  onProviderChange,
  onResourceChange,
  onDefaultResourceChange,
  onVectorSelectionModeChange,
  onNamespacePrefixChange,
}: PlatformDeploymentCapabilitySectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <div className="card-stack">
      <label className="card-stack">
        <span className="field-label">
          {t("platformControl.forms.deployment.providerForCapability", {
            capability: section.capability.display_name,
          })}
        </span>
        <select
          className="field-input"
          value={section.selectedProviderId}
          onChange={(event) => onProviderChange(event.target.value)}
        >
          <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
          {section.capabilityProviders.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.display_name}
            </option>
          ))}
        </select>
      </label>
      {section.capabilityMode === "model" ? (
        <ModelCapabilityFields
          section={section}
          onResourceChange={onResourceChange}
          onDefaultResourceChange={onDefaultResourceChange}
        />
      ) : section.capabilityMode === "vector" ? (
        <VectorCapabilityFields
          section={section}
          onResourceChange={onResourceChange}
          onVectorSelectionModeChange={onVectorSelectionModeChange}
          onNamespacePrefixChange={onNamespacePrefixChange}
        />
      ) : null}
    </div>
  );
}
