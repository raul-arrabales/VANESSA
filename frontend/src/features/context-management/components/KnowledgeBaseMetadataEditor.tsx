import { useTranslation } from "react-i18next";
import type { KnowledgeBaseSchemaProperty } from "../../../api/context";
import {
  createEmptyMetadataEntry,
  getMetadataPropertyType,
} from "../metadataEditor";
import type { MetadataEntryFormState } from "../types";

type Props = {
  schemaProperties: KnowledgeBaseSchemaProperty[];
  entries: MetadataEntryFormState[];
  onChange: (entries: MetadataEntryFormState[]) => void;
};

export function KnowledgeBaseMetadataEditor({
  schemaProperties,
  entries,
  onChange,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  const propertyNames = schemaProperties.map((property) => property.name);

  return (
    <section className="card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h5 className="section-title">{t("contextManagement.metadataEditor.title")}</h5>
          <p className="status-text">{t("contextManagement.metadataEditor.description")}</p>
        </div>
      </div>
      {schemaProperties.length === 0 ? (
        <p className="status-text">{t("contextManagement.metadataEditor.noSchemaProperties")}</p>
      ) : null}
      {schemaProperties.length > 0 && entries.length === 0 ? (
        <p className="status-text">{t("contextManagement.metadataEditor.empty")}</p>
      ) : null}
      {entries.map((entry) => {
        const propertyType = getMetadataPropertyType(entry.propertyName, schemaProperties);
        const availablePropertyNames = propertyNames.filter((propertyName) => {
          if (propertyName === entry.propertyName) {
            return true;
          }
          return !entries.some((candidate) => candidate.id !== entry.id && candidate.propertyName === propertyName);
        });

        return (
          <div key={entry.id} className="context-metadata-editor-row">
            <label className="card-stack" htmlFor={`metadata-property-${entry.id}`}>
              <span className="field-label">{t("contextManagement.metadataEditor.propertyName")}</span>
              <select
                id={`metadata-property-${entry.id}`}
                className="field-input"
                value={entry.propertyName}
                onChange={(event) => {
                  const value = event.currentTarget.value;
                  onChange(entries.map((candidate) => (candidate.id === entry.id ? { ...candidate, propertyName: value } : candidate)));
                }}
              >
                <option value="">{t("contextManagement.metadataEditor.selectProperty")}</option>
                {availablePropertyNames.map((propertyName) => (
                  <option key={propertyName} value={propertyName}>
                    {propertyName}
                  </option>
                ))}
              </select>
            </label>
            <label className="card-stack" htmlFor={`metadata-value-${entry.id}`}>
              <span className="field-label">{t("contextManagement.metadataEditor.propertyValue")}</span>
              {propertyType === "boolean" ? (
                <select
                  id={`metadata-value-${entry.id}`}
                  className="field-input"
                  value={entry.value}
                  onChange={(event) => {
                    const value = event.currentTarget.value;
                    onChange(entries.map((candidate) => (candidate.id === entry.id ? { ...candidate, value } : candidate)));
                  }}
                >
                  <option value="">{t("contextManagement.metadataEditor.selectBooleanValue")}</option>
                  <option value="true">{t("contextManagement.metadataEditor.booleanTrue")}</option>
                  <option value="false">{t("contextManagement.metadataEditor.booleanFalse")}</option>
                </select>
              ) : (
                <input
                  id={`metadata-value-${entry.id}`}
                  className="field-input"
                  inputMode={propertyType === "number" || propertyType === "int" ? "numeric" : undefined}
                  step={propertyType === "int" ? "1" : propertyType === "number" ? "any" : undefined}
                  value={entry.value}
                  onChange={(event) => {
                    const value = event.currentTarget.value;
                    onChange(entries.map((candidate) => (candidate.id === entry.id ? { ...candidate, value } : candidate)));
                  }}
                />
              )}
            </label>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => onChange(entries.filter((candidate) => candidate.id !== entry.id))}
              >
                {t("contextManagement.metadataEditor.remove")}
              </button>
            </div>
          </div>
        );
      })}
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={schemaProperties.length === 0 || entries.length >= schemaProperties.length}
          onClick={() => onChange([...entries, createEmptyMetadataEntry()])}
        >
          {t("contextManagement.metadataEditor.add")}
        </button>
      </div>
    </section>
  );
}
