import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
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

type McpRegistryIconName = "edit" | "enable" | "disable" | "validate" | "delete" | "description";
type McpValidationBadge = {
  label: string;
  tone: "active" | "inactive" | "optional" | "required";
};

function truncateWords(value: string, limit = 16): string {
  const words = value.trim().split(/\s+/).filter(Boolean);
  if (words.length <= limit) {
    return value;
  }
  return `${words.slice(0, limit).join(" ")}...`;
}

function McpRegistryIcon({ name }: { name: McpRegistryIconName }): JSX.Element {
  if (name === "edit") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M4 17.25V20h2.75L17.81 8.94l-2.75-2.75L4 17.25Zm15.71-10.04a1 1 0 0 0 0-1.42l-1.5-1.5a1 1 0 0 0-1.42 0l-1.02 1.02 2.75 2.75 1.19-1.19Z" />
      </svg>
    );
  }
  if (name === "enable") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M11 3h2v9h-2V3Zm5.42 2.58 1.42 1.42A8 8 0 1 1 6.16 7L7.58 5.58a6 6 0 1 0 8.84 0Z" />
      </svg>
    );
  }
  if (name === "disable") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M11 3h2v8h-2V3Zm7.78 3.81-1.42 1.42A6 6 0 0 1 8.23 16.7L6.8 18.13A8 8 0 0 0 18.78 6.81ZM4.22 4.22 2.81 5.64l3.01 3.01A8 8 0 0 0 5.87 18l-2.46 2.46 1.42 1.41L21.87 4.83l-1.41-1.42-2.62 2.62a8.03 8.03 0 0 0-3.06-1.75v2.11c.56.2 1.08.49 1.55.84L7.26 16.3a5.99 5.99 0 0 1 .02-6.22L4.22 4.22Z" />
      </svg>
    );
  }
  if (name === "validate") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-1.1 13.7-3.6-3.6 1.4-1.4 2.2 2.17 4.78-4.77 1.42 1.42-6.2 6.18Z" />
      </svg>
    );
  }
  if (name === "delete") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M8 4h8l1 2h4v2H3V6h4l1-2Zm1 6h2v8H9v-8Zm4 0h2v8h-2v-8ZM6 10h12l-1 10H7L6 10Z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 4h16v16H4V4Zm3 4h10V6H7v2Zm0 4h10v-2H7v2Zm0 4h7v-2H7v2Z" />
    </svg>
  );
}

function mcpValidationBadge(
  server: CatalogMcpServer,
  validation: CatalogMcpServerValidation["validation"] | undefined,
  isValidating: boolean,
  t: (key: string) => string,
): McpValidationBadge {
  if (isValidating) {
    return {
      label: t("catalogControl.mcp.validationBadges.validating"),
      tone: "optional",
    };
  }
  if (validation) {
    return validation.valid
      ? { label: t("catalogControl.mcp.validationBadges.validated"), tone: "active" }
      : { label: t("catalogControl.mcp.validationBadges.failed"), tone: "inactive" };
  }

  const runtimeStatus = String(server.runtime_status.runtime_status || "unknown").toLowerCase();
  if (runtimeStatus === "success" && server.runtime_status.is_validation_current) {
    return {
      label: t("catalogControl.mcp.validationBadges.validated"),
      tone: "active",
    };
  }
  if (runtimeStatus === "failed") {
    return {
      label: t("catalogControl.mcp.validationBadges.failed"),
      tone: "inactive",
    };
  }
  if (runtimeStatus === "success" && !server.runtime_status.is_validation_current) {
    return {
      label: t("catalogControl.mcp.validationBadges.stale"),
      tone: "optional",
    };
  }
  return {
    label: t("catalogControl.mcp.validationBadges.unvalidated"),
    tone: "required",
  };
}

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
  const [descriptionServer, setDescriptionServer] = useState<CatalogMcpServer | null>(null);
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
      <div className="catalog-mcp-registry-list" role="list">
        {filteredServers.map((server) => {
          const validation = validationResults[server.id]?.validation;
          const isValidating = validatingMcpServerId === server.id;
          const validationBadge = mcpValidationBadge(server, validation, isValidating, t);
          const backingToolName = toolNames.get(server.spec.backing_tool_id) ?? server.spec.backing_tool_id;
          const toggleLabel = server.spec.enabled
            ? t("catalogControl.mcp.actionLabels.disable", { name: server.spec.name })
            : t("catalogControl.mcp.actionLabels.enable", { name: server.spec.name });
          return (
            <article key={server.id} className="catalog-mcp-registry-item" role="listitem">
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
                <button type="button" className="catalog-icon-button" onClick={() => setDescriptionServer(server)} aria-label={t("catalogControl.mcp.actionLabels.description", { name: server.spec.name })} title={t("catalogControl.mcp.actionLabels.description", { name: server.spec.name })}>
                  <McpRegistryIcon name="description" />
                </button>
                <button type="button" className="catalog-icon-button" onClick={() => onEdit(server)} aria-label={t("catalogControl.mcp.actionLabels.edit", { name: server.spec.name })} title={t("catalogControl.mcp.actionLabels.edit", { name: server.spec.name })}>
                  <McpRegistryIcon name="edit" />
                </button>
                <button type="button" className="catalog-icon-button" onClick={() => onToggle(server)} aria-label={toggleLabel} title={toggleLabel}>
                  <McpRegistryIcon name={server.spec.enabled ? "disable" : "enable"} />
                </button>
                <button type="button" className="catalog-icon-button" onClick={() => onValidate(server.id)} disabled={isValidating} aria-label={isValidating ? t("catalogControl.mcp.actionLabels.validating", { name: server.spec.name }) : t("catalogControl.mcp.actionLabels.validate", { name: server.spec.name })} title={isValidating ? t("catalogControl.mcp.actionLabels.validating", { name: server.spec.name }) : t("catalogControl.mcp.actionLabels.validate", { name: server.spec.name })}>
                  <McpRegistryIcon name="validate" />
                </button>
                <button type="button" className="catalog-icon-button catalog-icon-button-danger" onClick={() => onDelete(server)} aria-label={t("catalogControl.mcp.actionLabels.delete", { name: server.spec.name })} title={t("catalogControl.mcp.actionLabels.delete", { name: server.spec.name })}>
                  <McpRegistryIcon name="delete" />
                </button>
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
        })}
      </div>
      {descriptionServer ? (
        <ModalDialog
          title={t("catalogControl.mcp.descriptionDialog.title", { name: descriptionServer.spec.name })}
          description={t("catalogControl.mcp.descriptionDialog.description")}
          className="catalog-description-modal"
          onClose={() => setDescriptionServer(null)}
          actions={(
            <button type="button" className="btn btn-secondary" onClick={() => setDescriptionServer(null)}>
              {t("catalogControl.mcp.descriptionDialog.close")}
            </button>
          )}
        >
          <div className="catalog-description-modal-body" tabIndex={0}>
            <p>{descriptionServer.spec.description}</p>
          </div>
        </ModalDialog>
      ) : null}
    </article>
  );
}
