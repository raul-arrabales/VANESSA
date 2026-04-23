import { useTranslation } from "react-i18next";
import type { CatalogAgent, CatalogAgentValidation } from "../../../api/catalog";

type CatalogAgentsDirectoryProps = {
  agents: CatalogAgent[];
  validationResults: Record<string, CatalogAgentValidation>;
  validatingAgentId: string;
  onEdit: (agent: CatalogAgent) => void;
  onValidate: (agentId: string) => void;
};

export default function CatalogAgentsDirectory({
  agents,
  validationResults,
  validatingAgentId,
  onEdit,
  onValidate,
}: CatalogAgentsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.agents.listTitle")}</h3>
        <p className="status-text">{t("catalogControl.agents.description")}</p>
      </div>

      <div className="catalog-grid">
        {agents.map((agent) => {
          const validation = validationResults[agent.id]?.validation;
          return (
            <article key={agent.id} className="platform-capability-card">
              <div className="platform-card-header">
                <h4 className="section-title">{agent.spec.name}</h4>
                <span className="platform-badge" data-tone={agent.published ? "active" : "required"}>
                  {agent.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                </span>
              </div>
              <p className="status-text">{agent.spec.description}</p>
              <p className="status-text">
                <code className="code-inline">{agent.id}</code>
              </p>
              <p className="status-text">{t("catalogControl.summary.version", { version: agent.current_version })}</p>
              <div className="status-row">
                <button type="button" className="btn btn-secondary" onClick={() => onEdit(agent)}>
                  {t("catalogControl.actions.edit")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => onValidate(agent.id)} disabled={validatingAgentId === agent.id}>
                  {validatingAgentId === agent.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
                </button>
              </div>
              {validation ? (
                <div className="card-stack">
                  <span className="field-label">
                    {validation.valid ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
                  </span>
                  {validation.errors.length > 0 ? (
                    <ul className="status-text">
                      {validation.errors.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </article>
  );
}
