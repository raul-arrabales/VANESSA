import { useTranslation } from "react-i18next";
import type { CatalogTool, CatalogToolValidation } from "../../../api/catalog";

type CatalogToolsDirectoryProps = {
  tools: CatalogTool[];
  validationResults: Record<string, CatalogToolValidation>;
  validatingToolId: string;
  onEdit: (tool: CatalogTool) => void;
  onValidate: (toolId: string) => void;
};

export default function CatalogToolsDirectory({
  tools,
  validationResults,
  validatingToolId,
  onEdit,
  onValidate,
}: CatalogToolsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.tools.listTitle")}</h3>
        <p className="status-text">{t("catalogControl.tools.description")}</p>
      </div>

      <div className="catalog-grid">
        {tools.map((tool) => {
          const validation = validationResults[tool.id]?.validation;
          return (
            <article key={tool.id} className="platform-capability-card">
              <div className="platform-card-header">
                <h4 className="section-title">{tool.spec.name}</h4>
                <span className="platform-badge" data-tone={tool.published ? "active" : "required"}>
                  {tool.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                </span>
              </div>
              <p className="status-text">{tool.spec.description}</p>
              <p className="status-text">
                <code className="code-inline">{tool.id}</code>
              </p>
              <p className="status-text">
                {t("catalogControl.tools.transportLabel", {
                  transport: t(`catalogControl.transport.${tool.spec.transport === "mcp" ? "mcp" : "sandbox"}`),
                })}
              </p>
              <div className="status-row">
                <button type="button" className="btn btn-secondary" onClick={() => onEdit(tool)}>
                  {t("catalogControl.actions.edit")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => onValidate(tool.id)} disabled={validatingToolId === tool.id}>
                  {validatingToolId === tool.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
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
