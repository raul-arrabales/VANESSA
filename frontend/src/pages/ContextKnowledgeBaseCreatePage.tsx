import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { createKnowledgeBase } from "../api/context";
import { useAuth } from "../auth/AuthProvider";
import { useActionFeedback, withActionFeedbackState } from "../feedback/ActionFeedbackProvider";

export default function ContextKnowledgeBaseCreatePage(): JSX.Element {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showErrorFeedback } = useActionFeedback();
  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [schemaText, setSchemaText] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    let schema: Record<string, unknown> | undefined;
    if (schemaText.trim()) {
      try {
        schema = JSON.parse(schemaText) as Record<string, unknown>;
      } catch {
        showErrorFeedback(t("contextManagement.feedback.invalidSchema"), t("contextManagement.feedback.createFailed"));
        return;
      }
    }
    setSaving(true);
    try {
      const knowledgeBase = await createKnowledgeBase({
        slug,
        display_name: displayName,
        description,
        backing_provider_key: "weaviate_local",
        lifecycle_state: "active",
        schema,
      }, token);
      navigate(`/control/context/${knowledgeBase.id}`, {
        state: withActionFeedbackState({
          kind: "success",
          message: t("contextManagement.feedback.created", { name: knowledgeBase.display_name }),
        }),
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("contextManagement.feedback.createFailed"));
    } finally {
      setSaving(false);
    }
  }

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
