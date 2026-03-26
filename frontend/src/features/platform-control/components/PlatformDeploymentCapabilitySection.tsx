import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import type { DeploymentCapabilitySectionState, DeploymentModelCheckboxOption } from "../deploymentFormSections";

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
  onDefaultResourceChange: (resourceId: string) => void;
  onVectorSelectionModeChange: (selectionMode: string) => void;
  onNamespacePrefixChange: (namespacePrefix: string) => void;
};

type ResourcePickerProps = {
  capabilityDisplayName: string;
  selectedResourceIds: string[];
  resourcePickerSummary: string;
  options: DeploymentModelCheckboxOption[];
  helperHints?: string[];
  onResourceChange: (resourceIds: string[]) => void;
};

function buildNextSelectedResourceIds(
  options: DeploymentModelCheckboxOption[],
  selectedResourceIds: string[],
  resourceId: string,
  checked: boolean,
): string[] {
  const selectedIds = new Set(selectedResourceIds);
  if (checked) {
    selectedIds.add(resourceId);
  } else {
    selectedIds.delete(resourceId);
  }
  return options.filter((option) => selectedIds.has(option.id)).map((option) => option.id);
}

function ResourcePicker({
  capabilityDisplayName,
  selectedResourceIds,
  resourcePickerSummary,
  options,
  helperHints = [],
  onResourceChange,
}: ResourcePickerProps): JSX.Element {
  const { t } = useTranslation("common");
  const [isOpen, setIsOpen] = useState(false);
  const panelId = useId();
  const pickerCountLabel = t("platformControl.forms.deployment.resourcePickerCount", {
    count: selectedResourceIds.length,
  });

  return (
    <div className="card-stack deployment-binding-field deployment-resource-picker">
      <span className="field-label">{t("platformControl.forms.deployment.boundResources")}</span>
      <button
        type="button"
        className="field-input deployment-resource-trigger"
        aria-label={t("platformControl.forms.deployment.resourcesForCapability", {
          capability: capabilityDisplayName,
        })}
        aria-controls={panelId}
        aria-expanded={isOpen}
        disabled={options.length === 0}
        onClick={() => setIsOpen((current) => !current)}
      >
        <span className="deployment-resource-trigger-text">{resourcePickerSummary}</span>
        <span className="deployment-resource-trigger-meta">{pickerCountLabel}</span>
      </button>
      {isOpen ? (
        <div id={panelId} className="deployment-resource-panel">
          {options.map((option) => (
            <label key={option.id} className="deployment-resource-option">
              <input
                type="checkbox"
                checked={option.selected}
                onChange={(event) =>
                  onResourceChange(
                    buildNextSelectedResourceIds(options, selectedResourceIds, option.id, event.target.checked),
                  )
                }
              />
              <span>{option.name}</span>
            </label>
          ))}
        </div>
      ) : null}
      {helperHints.map((hint) => (
        <p key={hint} className="status-text">{hint}</p>
      ))}
    </div>
  );
}

function ModelCapabilityFields({
  section,
  onResourceChange,
  onDefaultResourceChange,
}: ModelCapabilityFieldsProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <ResourcePicker
        capabilityDisplayName={section.capability.display_name}
        selectedResourceIds={section.selectedResourceIds}
        resourcePickerSummary={section.resourcePickerSummary}
        options={section.modelCheckboxOptions}
        helperHints={[
          section.loadedModelEligibilityHint,
          section.noEligibleResourcesHint,
        ].filter((hint): hint is string => Boolean(hint))}
        onResourceChange={onResourceChange}
      />
      <label className="card-stack deployment-binding-field">
        <span className="field-label">{t("platformControl.forms.deployment.defaultResource")}</span>
        <select
          className="field-input"
          aria-label={t("platformControl.forms.deployment.defaultResourceForCapability", {
            capability: section.capability.display_name,
          })}
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
  onDefaultResourceChange,
  onVectorSelectionModeChange,
  onNamespacePrefixChange,
}: VectorCapabilityFieldsProps): JSX.Element {
  const { t } = useTranslation("common");
  const knowledgeBaseOptions = section.vectorKnowledgeBases.map((knowledgeBase) => ({
    id: knowledgeBase.id,
    name: knowledgeBase.display_name,
    selected: section.selectedResourceIds.includes(knowledgeBase.id),
  }));

  return (
    <>
      <label className="card-stack deployment-binding-field">
        <span className="field-label">{t("platformControl.forms.deployment.selectionMode")}</span>
        <select
          className="field-input"
          aria-label={t("platformControl.forms.deployment.vectorSelectionMode")}
          value={section.vectorSelectionMode}
          onChange={(event) => onVectorSelectionModeChange(event.target.value)}
        >
          <option value="explicit">{t("platformControl.forms.deployment.vectorSelectionModeExplicit")}</option>
          <option value="dynamic_namespace">{t("platformControl.forms.deployment.vectorSelectionModeDynamic")}</option>
        </select>
      </label>
      {section.vectorSelectionMode === "dynamic_namespace" ? (
        <label className="card-stack deployment-binding-field">
          <span className="field-label">{t("platformControl.forms.deployment.namespacePrefix")}</span>
          <input
            className="field-input"
            value={section.namespacePrefix}
            onChange={(event) => onNamespacePrefixChange(event.target.value)}
          />
        </label>
      ) : (
        <>
          <ResourcePicker
            capabilityDisplayName={section.capability.display_name}
            selectedResourceIds={section.selectedResourceIds}
            resourcePickerSummary={section.resourcePickerSummary}
            options={knowledgeBaseOptions}
            onResourceChange={onResourceChange}
          />
          <label className="card-stack deployment-binding-field">
            <span className="field-label">{t("platformControl.forms.deployment.defaultResource")}</span>
            <select
              className="field-input"
              aria-label={t("platformControl.forms.deployment.defaultResourceForCapability", {
                capability: section.capability.display_name,
              })}
              value={section.defaultResourceId}
              disabled={section.vectorDefaultResources.length === 0}
              onChange={(event) => onDefaultResourceChange(event.target.value)}
            >
              <option value="">{t("platformControl.forms.selectPlaceholder")}</option>
              {section.vectorDefaultResources.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.display_name}
                </option>
              ))}
            </select>
          </label>
        </>
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
  const rowTitleId = useId();

  return (
    <section
      className="deployment-binding-row panel"
      aria-labelledby={rowTitleId}
      data-testid={`deployment-binding-row-${section.capabilityKey}`}
    >
      <div className="deployment-binding-heading">
        <span className="field-label">{t("platformControl.forms.deployment.binding")}</span>
        <h4 id={rowTitleId} className="deployment-binding-title">
          {section.capability.display_name}
        </h4>
        <p className="status-text">{section.capability.description}</p>
      </div>

      <label className="card-stack deployment-binding-field">
        <span className="field-label">{t("platformControl.forms.deployment.provider")}</span>
        <select
          className="field-input"
          aria-label={t("platformControl.forms.deployment.providerForCapability", {
            capability: section.capability.display_name,
          })}
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
          onDefaultResourceChange={onDefaultResourceChange}
          onVectorSelectionModeChange={onVectorSelectionModeChange}
          onNamespacePrefixChange={onNamespacePrefixChange}
        />
      ) : null}
    </section>
  );
}
