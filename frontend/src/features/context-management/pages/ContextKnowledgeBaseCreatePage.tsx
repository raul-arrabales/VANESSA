import { useTranslation } from "react-i18next";
import { useContextKnowledgeBaseCreate } from "../hooks/useContextKnowledgeBaseCreate";

export default function ContextKnowledgeBaseCreatePage(): JSX.Element {
  const { t } = useTranslation("common");
  const {
    slug,
    displayName,
    description,
    schemaText,
    saving,
    setSlug,
    setDisplayName,
    setDescription,
    setSchemaText,
    handleSubmit,
  } = useContextKnowledgeBaseCreate();

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("contextManagement.createTitle")}</h2>
      <p className="status-text">{t("contextManagement.createDescription")}</p>
      <form className="card-stack" onSubmit={(event) => void handleSubmit(event)}>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.slug")}</span>
          <input className="field-input" value={slug} onChange={(event) => setSlug(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.displayName")}</span>
          <input className="field-input" value={displayName} onChange={(event) => setDisplayName(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("platformControl.forms.deployment.description")}</span>
          <textarea className="field-input quote-admin-textarea" value={description} onChange={(event) => setDescription(event.currentTarget.value)} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("contextManagement.fields.schema")}</span>
          <textarea
            className="field-input quote-admin-textarea"
            value={schemaText}
            onChange={(event) => setSchemaText(event.currentTarget.value)}
            placeholder='{"properties":[{"name":"title","data_type":"text"}]}'
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? t("platformControl.actions.saving") : t("contextManagement.actions.create")}
          </button>
        </div>
      </form>
    </section>
  );
}
