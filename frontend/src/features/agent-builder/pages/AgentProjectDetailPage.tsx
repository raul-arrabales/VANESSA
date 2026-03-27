import { useTranslation } from "react-i18next";
import { AgentProjectFormFields } from "../components/AgentProjectFormFields";
import { useAgentProjectEditor } from "../hooks/useAgentProjectEditor";
import { useAgentProjectPreview } from "../hooks/useAgentProjectPreview";

export default function AgentProjectDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useAgentProjectEditor();
  const preview = useAgentProjectPreview(detail.projectId, detail.form);

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="platform-card-header">
          <div className="card-stack">
            <h2 className="section-title">{detail.project?.spec.name ?? t("agentBuilder.detailTitle")}</h2>
            <p className="status-text">{detail.project?.spec.description ?? t("agentBuilder.detailDescription")}</p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={detail.handleBack}>
            {t("agentBuilder.actions.back")}
          </button>
        </div>
        {detail.loading ? <p className="status-text">{t("agentBuilder.states.loading")}</p> : null}
        {!detail.loading ? (
          <form className="card-stack" onSubmit={(event) => void detail.handleSave(event)}>
            <AgentProjectFormFields form={detail.form} setForm={detail.setForm} disableId />
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={detail.saving}>
                {detail.saving ? t("agentBuilder.actions.saving") : t("agentBuilder.actions.save")}
              </button>
              <button type="button" className="btn btn-secondary" disabled={detail.validating} onClick={() => void detail.handleValidate()}>
                {detail.validating ? t("agentBuilder.actions.validating") : t("agentBuilder.actions.validate")}
              </button>
              <button type="button" className="btn btn-secondary" disabled={detail.publishing} onClick={() => void detail.handlePublish()}>
                {detail.publishing ? t("agentBuilder.actions.publishing") : t("agentBuilder.actions.publish")}
              </button>
            </div>
          </form>
        ) : null}
      </article>

      <article className="panel card-stack">
        <h3 className="section-title">{t("agentBuilder.previewTitle")}</h3>
        <p className="status-text">{t("agentBuilder.previewDescription")}</p>
        <p className="status-text">{t("agentBuilder.preview.assistantRef")}: {preview.assistantRef}</p>
        <p className="status-text">{t("agentBuilder.preview.playgroundKind")}: {preview.playgroundKind}</p>
        <p className="status-text">{t("agentBuilder.preview.defaultModelRef")}: {preview.defaultModelRef ?? t("agentBuilder.preview.none")}</p>
        <p className="status-text">{t("agentBuilder.preview.toolRefs")}: {preview.toolRefs.join(", ") || t("agentBuilder.preview.none")}</p>
      </article>

      {detail.validation ? (
        <article className="panel card-stack">
          <h3 className="section-title">{t("agentBuilder.validationTitle")}</h3>
          <p className="status-text">{detail.validation.validation.valid ? t("agentBuilder.validation.valid") : t("agentBuilder.validation.invalid")}</p>
          {detail.validation.validation.errors.map((error) => (
            <p key={error} className="status-text error-text">{error}</p>
          ))}
        </article>
      ) : null}

      {detail.publishResult ? (
        <article className="panel card-stack">
          <h3 className="section-title">{t("agentBuilder.publishTitle")}</h3>
          <p className="status-text">{detail.publishResult.publish_result.agent_id}</p>
          <p className="status-text">{detail.publishResult.publish_result.published_at}</p>
        </article>
      ) : null}
    </section>
  );
}
