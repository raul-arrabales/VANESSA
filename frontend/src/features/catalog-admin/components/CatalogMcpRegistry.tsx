import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer, CatalogMcpServerValidation, CatalogTool } from "../../../api/catalog";

type CatalogMcpRegistryProps = {
  mcpServers: CatalogMcpServer[];
  tools: CatalogTool[];
  validationResults: Record<string, CatalogMcpServerValidation>;
  validatingMcpServerId: string;
  onEdit: (server: CatalogMcpServer) => void;
  onDelete: (server: CatalogMcpServer) => void;
  onToggle: (server: CatalogMcpServer) => void;
  onValidate: (serverId: string) => void;
};

export default function CatalogMcpRegistry({
  mcpServers,
  tools,
  validationResults,
  validatingMcpServerId,
  onEdit,
  onDelete,
  onToggle,
  onValidate,
}: CatalogMcpRegistryProps): JSX.Element {
  const { t } = useTranslation("common");
  const [query, setQuery] = useState("");
  const toolNames = useMemo(() => new Map(tools.map((tool) => [tool.id, tool.spec.name])), [tools]);
  const filteredServers = mcpServers.filter((server) => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return true;
    }
    return [server.spec.name, server.spec.slug, server.spec.backing_tool_id].some((value) => value.toLowerCase().includes(needle));
  });

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.mcp.registryTitle")}</h3>
        <input
          className="field-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("catalogControl.mcp.searchPlaceholder")}
        />
      </div>
      <div className="catalog-grid">
        {filteredServers.map((server) => {
          const validation = validationResults[server.id]?.validation;
          return (
            <article key={server.id} className="platform-capability-card">
              <div className="platform-card-header">
                <h4 className="section-title">{server.spec.name}</h4>
                <span className="platform-badge" data-tone={server.spec.enabled ? "active" : "required"}>
                  {server.spec.enabled ? t("catalogControl.badges.enabled") : t("catalogControl.badges.disabled")}
                </span>
              </div>
              <p className="status-text">{server.spec.description}</p>
              <p className="status-text"><code className="code-inline">{server.spec.slug}</code></p>
              <p className="status-text">{t("catalogControl.mcp.backingToolLabel", { tool: toolNames.get(server.spec.backing_tool_id) ?? server.spec.backing_tool_id })}</p>
              <p className="status-text">{t("catalogControl.mcp.domainLabel", { domains: server.spec.authorization_policy.agent_domains.join(", ") })}</p>
              <p className="status-text">{t("catalogControl.mcp.updatedLabel", { updated: server.updated_at ?? server.published_at ?? "-" })}</p>
              <div className="status-row">
                <button type="button" className="btn btn-secondary" onClick={() => onEdit(server)}>{t("catalogControl.actions.edit")}</button>
                <button type="button" className="btn btn-secondary" onClick={() => onToggle(server)}>
                  {server.spec.enabled ? t("catalogControl.actions.disable") : t("catalogControl.actions.enable")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => onValidate(server.id)} disabled={validatingMcpServerId === server.id}>
                  {validatingMcpServerId === server.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => onDelete(server)}>{t("catalogControl.actions.delete")}</button>
              </div>
              {validation ? (
                <div className="card-stack">
                  <span className="field-label">{validation.valid ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}</span>
                  {validation.errors.length > 0 ? (
                    <ul className="status-text">
                      {validation.errors.map((message) => <li key={message}>{message}</li>)}
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
