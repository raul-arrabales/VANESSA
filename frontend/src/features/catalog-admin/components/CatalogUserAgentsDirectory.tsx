import ActionIcon from "../../../components/ActionIcon";
import {
  CompactRegistryActions,
  CompactRegistryDescription,
  CompactRegistryHeading,
  CompactRegistryItem,
  CompactRegistryList,
  CompactRegistryMain,
  CompactRegistryMeta,
  CompactRegistryProgress,
} from "../../../components/CompactRegistryList";
import IconButton from "../../../components/IconButton";
import { useTranslation } from "react-i18next";
import type { AgentProject, AgentProjectValidation } from "../../../api/agentProjects";

type Props = {
  projects: AgentProject[];
  loading: boolean;
  validatingProjectId: string;
  publishingProjectId: string;
  deletingProjectId: string;
  validations: Record<string, AgentProjectValidation>;
  onEdit: (project: AgentProject) => void;
  onValidate: (projectId: string) => void;
  onPublish: (projectId: string) => void;
  onDelete: (project: AgentProject) => void;
};

export default function CatalogUserAgentsDirectory({
  projects,
  loading,
  validatingProjectId,
  publishingProjectId,
  deletingProjectId,
  validations,
  onEdit,
  onValidate,
  onPublish,
  onDelete,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.agents.userListTitle")}</h3>
        <p className="status-text">{t("catalogControl.agents.userProjects.directoryDescription")}</p>
      </div>
      {loading ? <p className="status-text">{t("catalogControl.agents.userProjects.loading")}</p> : null}
      <CompactRegistryList>
        {!loading && projects.length === 0 ? <p className="status-text">{t("catalogControl.agents.emptyUser")}</p> : null}
        {projects.map((project) => {
          const validation = validations[project.id]?.validation;
          const validateLabel = validatingProjectId === project.id
            ? t("catalogControl.agents.userProjects.actionLabels.validating", { name: project.spec.name })
            : t("catalogControl.agents.userProjects.actionLabels.validate", { name: project.spec.name });
          const publishLabel = publishingProjectId === project.id
            ? t("catalogControl.agents.userProjects.actionLabels.publishing", { name: project.spec.name })
            : t("catalogControl.agents.userProjects.actionLabels.publish", { name: project.spec.name });
          const deleteLabel = deletingProjectId === project.id
            ? t("catalogControl.agents.userProjects.actionLabels.deleting", { name: project.spec.name })
            : t("catalogControl.agents.userProjects.actionLabels.delete", { name: project.spec.name });

          return (
            <CompactRegistryItem key={project.id}>
              <CompactRegistryMain>
                <CompactRegistryHeading>
                  <h4 className="section-title">{project.spec.name}</h4>
                  <span className="platform-badge" data-tone={project.published_agent_id ? "active" : "required"}>
                    {project.published_agent_id ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                  </span>
                  {validation ? (
                    <span className="platform-badge" data-tone={validation.valid ? "active" : "inactive"}>
                      {validation.valid ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
                    </span>
                  ) : (
                    <span className="platform-badge" data-tone="required">
                      {t("catalogControl.agents.validationBadges.unvalidated")}
                    </span>
                  )}
                  {project.spec.runtime_constraints.internet_required ? (
                    <span className="platform-badge" data-tone="optional">
                      {t("catalogControl.agents.internetRequired")}
                    </span>
                  ) : null}
                  {project.spec.runtime_constraints.sandbox_required ? (
                    <span className="platform-badge" data-tone="optional">
                      {t("catalogControl.agents.sandboxRequired")}
                    </span>
                  ) : null}
                </CompactRegistryHeading>
                <CompactRegistryDescription>{project.spec.description}</CompactRegistryDescription>
                <CompactRegistryMeta>
                  <code className="code-inline">{project.id}</code>
                  <span>{t("catalogControl.summary.version", { version: project.current_version })}</span>
                  <span>{t("catalogControl.agents.userProjects.agentTypeLabel", { type: project.spec.agent_type })}</span>
                  <span>{t("catalogControl.agents.userProjects.channelLabel", { channel: project.spec.channel_type })}</span>
                  <span>{t("catalogControl.agents.userProjects.interfaceLabel", { interface: project.spec.interface_type })}</span>
                  <span>
                    {t("catalogControl.agents.userProjects.publishedAgentLabel", {
                      agentId: project.published_agent_id ?? t("catalogControl.agents.userProjects.notPublished"),
                    })}
                  </span>
                </CompactRegistryMeta>
              </CompactRegistryMain>
              <CompactRegistryActions label={t("catalogControl.agents.actionsFor", { name: project.spec.name })}>
                <IconButton label={t("catalogControl.agents.userProjects.actionLabels.edit", { name: project.spec.name })} onClick={() => onEdit(project)}>
                  <ActionIcon name="edit" />
                </IconButton>
                <IconButton label={validateLabel} onClick={() => void onValidate(project.id)} disabled={validatingProjectId === project.id}>
                  <ActionIcon name="validate" />
                </IconButton>
                <IconButton label={publishLabel} onClick={() => void onPublish(project.id)} disabled={publishingProjectId === project.id}>
                  <ActionIcon name="publish" />
                </IconButton>
                <IconButton label={deleteLabel} tone="danger" onClick={() => void onDelete(project)} disabled={deletingProjectId === project.id}>
                  <ActionIcon name="delete" />
                </IconButton>
              </CompactRegistryActions>
              {validation?.errors.length ? (
                <CompactRegistryProgress>
                  <ul className="status-text">
                    {validation.errors.map((error) => (
                      <li key={error}>{error}</li>
                    ))}
                  </ul>
                </CompactRegistryProgress>
              ) : null}
            </CompactRegistryItem>
          );
        })}
      </CompactRegistryList>
    </article>
  );
}
