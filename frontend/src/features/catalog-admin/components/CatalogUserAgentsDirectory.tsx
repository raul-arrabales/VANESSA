import { useTranslation } from "react-i18next";
import type { AgentProject, AgentProjectValidation } from "../../../api/agentProjects";

type Props = {
  projects: AgentProject[];
  loading: boolean;
  validatingProjectId: string;
  publishingProjectId: string;
  validations: Record<string, AgentProjectValidation>;
  onEdit: (project: AgentProject) => void;
  onValidate: (projectId: string) => void;
  onPublish: (projectId: string) => void;
};

export default function CatalogUserAgentsDirectory({
  projects,
  loading,
  validatingProjectId,
  publishingProjectId,
  validations,
  onEdit,
  onValidate,
  onPublish,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.agents.userListTitle")}</h3>
        <p className="status-text">{t("catalogControl.agents.userProjects.directoryDescription")}</p>
      </div>
      {loading ? <p className="status-text">{t("catalogControl.agents.userProjects.loading")}</p> : null}
      {!loading && projects.length === 0 ? <p className="status-text">{t("catalogControl.agents.emptyUser")}</p> : null}
      {projects.map((project) => {
        const validation = validations[project.id]?.validation;
        return (
          <article key={project.id} className="panel panel-nested card-stack">
            <div className="status-row">
              <div className="card-stack">
                <h4 className="section-title">{project.spec.name}</h4>
                <p className="status-text">{project.spec.description}</p>
              </div>
              <div className="toolbar">
                <button type="button" className="btn btn-secondary" onClick={() => onEdit(project)}>
                  {t("catalogControl.actions.edit")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={validatingProjectId === project.id}
                  onClick={() => void onValidate(project.id)}
                >
                  {validatingProjectId === project.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={publishingProjectId === project.id}
                  onClick={() => void onPublish(project.id)}
                >
                  {publishingProjectId === project.id ? t("catalogControl.actions.publishing") : t("catalogControl.agents.userProjects.publish")}
                </button>
              </div>
            </div>
            <div className="inline-meta-list">
              <span>{project.id}</span>
              <span>{project.spec.agent_type}</span>
              <span>{project.spec.channel_type}</span>
              <span>{project.spec.interface_type}</span>
              <span>{project.published_agent_id ?? t("catalogControl.agents.userProjects.notPublished")}</span>
            </div>
            {validation?.errors.length ? (
              <div className="card-stack">
                {validation.errors.map((error) => (
                  <p key={error} className="status-text error-text">{error}</p>
                ))}
              </div>
            ) : null}
          </article>
        );
      })}
    </article>
  );
}
