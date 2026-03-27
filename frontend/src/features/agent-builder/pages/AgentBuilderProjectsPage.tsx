import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AgentProjectFormFields } from "../components/AgentProjectFormFields";
import { useAgentProjects } from "../hooks/useAgentProjects";

export default function AgentBuilderProjectsPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { projects, loading, creating, errorMessage, form, setForm, handleCreate } = useAgentProjects();

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">{t("agentBuilder.title")}</h2>
        <p className="status-text">{t("agentBuilder.description")}</p>
        <form className="card-stack" onSubmit={(event) => void handleCreate(event)}>
          <AgentProjectFormFields form={form} setForm={setForm} />
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? t("agentBuilder.actions.creating") : t("agentBuilder.actions.create")}
            </button>
          </div>
        </form>
      </article>

      <article className="panel card-stack">
        <h3 className="section-title">{t("agentBuilder.projectsTitle")}</h3>
        <p className="status-text">{t("agentBuilder.projectsDescription")}</p>
        {errorMessage ? <p className="status-text error-text">{errorMessage}</p> : null}
        {loading ? <p className="status-text">{t("agentBuilder.states.loading")}</p> : null}
        {!loading && projects.length === 0 ? <p className="status-text">{t("agentBuilder.states.empty")}</p> : null}
        {projects.length > 0 ? (
          <div className="health-table-wrap">
            <table className="health-table" aria-label={t("agentBuilder.aria.table")}>
              <thead>
                <tr>
                  <th>{t("agentBuilder.columns.name")}</th>
                  <th>{t("agentBuilder.columns.visibility")}</th>
                  <th>{t("agentBuilder.columns.version")}</th>
                  <th>{t("agentBuilder.columns.published")}</th>
                  <th>{t("agentBuilder.columns.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.id}>
                    <td>
                      <strong>{project.spec.name}</strong>
                      <div className="platform-inline-meta">
                        <span className="status-text">{project.id}</span>
                      </div>
                    </td>
                    <td>{project.visibility}</td>
                    <td>{project.current_version}</td>
                    <td>{project.published_agent_id ?? t("agentBuilder.states.notPublished")}</td>
                    <td>
                      <Link className="btn btn-secondary" to={`/control/agent-builder/${project.id}`}>
                        {t("agentBuilder.actions.manage")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </section>
  );
}
