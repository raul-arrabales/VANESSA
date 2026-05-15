import { useTranslation } from "react-i18next";
import IconButton from "../../../components/IconButton";
import type { CatalogMcpServer, CatalogMcpServerValidation } from "../../../api/catalog";
import { getMcpValidationBadge } from "../mcpValidationBadge";
import CatalogMcpRegistryIcon from "./CatalogMcpRegistryIcon";

type CatalogMcpRegistryItemProps = {
  server: CatalogMcpServer;
  backingToolName: string;
  validation: CatalogMcpServerValidation["validation"] | undefined;
  isValidating: boolean;
  onEdit: (server: CatalogMcpServer) => void;
  onDelete: (server: CatalogMcpServer) => void;
  onToggle: (server: CatalogMcpServer) => void;
  onValidate: (serverId: string) => void;
  onViewDescription: (server: CatalogMcpServer) => void;
};

function truncateWords(value: string, limit = 16): string {
  const words = value.trim().split(/\s+/).filter(Boolean);
  if (words.length <= limit) {
    return value;
  }
  return `${words.slice(0, limit).join(" ")}...`;
}

export default function CatalogMcpRegistryItem({
  server,
  backingToolName,
  validation,
  isValidating,
  onEdit,
  onDelete,
  onToggle,
  onValidate,
  onViewDescription,
}: CatalogMcpRegistryItemProps): JSX.Element {
  const { t } = useTranslation("common");
  const validationBadge = getMcpValidationBadge(server, validation, isValidating, t);
  const toggleLabel = server.spec.enabled
    ? t("catalogControl.mcp.actionLabels.disable", { name: server.spec.name })
    : t("catalogControl.mcp.actionLabels.enable", { name: server.spec.name });
  const validateLabel = isValidating
    ? t("catalogControl.mcp.actionLabels.validating", { name: server.spec.name })
    : t("catalogControl.mcp.actionLabels.validate", { name: server.spec.name });

  return (
    <article className="catalog-mcp-registry-item" role="listitem">
      <div className="catalog-mcp-registry-main">
        <div className="catalog-mcp-registry-heading">
          <h4 className="section-title">{server.spec.name}</h4>
          <span className="platform-badge" data-tone={server.spec.enabled ? "active" : "required"}>
            {server.spec.enabled ? t("catalogControl.badges.enabled") : t("catalogControl.badges.disabled")}
          </span>
          <span className="platform-badge" data-tone={validationBadge.tone}>
            {validationBadge.label}
          </span>
        </div>
        <p className="status-text catalog-mcp-description-preview">{truncateWords(server.spec.description)}</p>
        <div className="catalog-mcp-meta-row">
          <code className="code-inline">{server.spec.slug}</code>
          <span>{t("catalogControl.mcp.backingToolLabel", { tool: backingToolName })}</span>
          <span>{t("catalogControl.mcp.domainLabel", { domains: server.spec.authorization_policy.agent_domains.join(", ") })}</span>
          <span>{t("catalogControl.mcp.updatedLabel", { updated: server.updated_at ?? server.published_at ?? "-" })}</span>
        </div>
      </div>
      <div className="catalog-mcp-registry-actions" role="group" aria-label={t("catalogControl.mcp.actionsFor", { name: server.spec.name })}>
        <IconButton label={t("catalogControl.mcp.actionLabels.description", { name: server.spec.name })} onClick={() => onViewDescription(server)}>
          <CatalogMcpRegistryIcon name="description" />
        </IconButton>
        <IconButton label={t("catalogControl.mcp.actionLabels.edit", { name: server.spec.name })} onClick={() => onEdit(server)}>
          <CatalogMcpRegistryIcon name="edit" />
        </IconButton>
        <IconButton label={toggleLabel} onClick={() => onToggle(server)}>
          <CatalogMcpRegistryIcon name={server.spec.enabled ? "disable" : "enable"} />
        </IconButton>
        <IconButton label={validateLabel} onClick={() => onValidate(server.id)} disabled={isValidating}>
          <CatalogMcpRegistryIcon name="validate" />
        </IconButton>
        <IconButton label={t("catalogControl.mcp.actionLabels.delete", { name: server.spec.name })} tone="danger" onClick={() => onDelete(server)}>
          <CatalogMcpRegistryIcon name="delete" />
        </IconButton>
      </div>
      {validation ? (
        <div className="catalog-mcp-validation">
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
}
