import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer, CatalogMcpServerValidation, CatalogTool } from "../../../api/catalog";
import { CompactRegistryList } from "../../../components/CompactRegistryList";
import { LifecycleGraphActionModal, useSelectedLifecycleItem } from "../../../components/lifecycle-graph";
import { createCatalogMcpLifecycleGraphDefinition, getCatalogMcpLifecycleState, getCatalogMcpLifecycleSummaryRows } from "../catalogMcpLifecycleGraph";
import CatalogMcpDescriptionModal from "./CatalogMcpDescriptionModal";
import CatalogMcpRegistryItem from "./CatalogMcpRegistryItem";
import { MCP_METADATA_CATEGORY_OPTIONS } from "../mcpMetadataOptions";

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
  const [categoryFilter, setCategoryFilter] = useState<CatalogMcpServer["spec"]["metadata"]["category"] | "">("");
  const [descriptionServer, setDescriptionServer] = useState<CatalogMcpServer | null>(null);
  const { selectedLifecycleItem, openLifecycleItem, closeLifecycleItem } = useSelectedLifecycleItem<CatalogMcpServer>();
  const lifecycleDefinition = useMemo(() => createCatalogMcpLifecycleGraphDefinition(t), [t]);
  const toolNames = useMemo(() => new Map(tools.map((tool) => [tool.id, tool.spec.name])), [tools]);
  const filteredServers = mcpServers.filter((server) => {
    if (categoryFilter && server.spec.metadata.category !== categoryFilter) {
      return false;
    }
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return true;
    }
    return [
      server.spec.name,
      server.spec.slug,
      server.spec.backing_tool_id,
      server.spec.metadata.category,
      server.spec.metadata.risk_level,
      ...server.spec.metadata.capabilities,
    ].some((value) => value.toLowerCase().includes(needle));
  });

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.mcp.registryTitle")}</h3>
        <div className="platform-filter-grid">
          <label className="card-stack" htmlFor="catalog-mcp-search">
            <span className="field-label">{t("catalogControl.mcp.filters.search")}</span>
            <input
              id="catalog-mcp-search"
              className="field-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("catalogControl.mcp.searchPlaceholder")}
            />
          </label>
          <label className="card-stack" htmlFor="catalog-mcp-type-filter">
            <span className="field-label">{t("catalogControl.mcp.filters.type")}</span>
            <select
              id="catalog-mcp-type-filter"
              className="field-input"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value as CatalogMcpServer["spec"]["metadata"]["category"] | "")}
            >
              <option value="">{t("catalogControl.mcp.filters.allTypes")}</option>
              {MCP_METADATA_CATEGORY_OPTIONS.map((category) => (
                <option key={category} value={category}>
                  {t(`catalogControl.mcp.metadata.category.${category}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {filteredServers.length === 0 ? <p className="status-text">{t("catalogControl.mcp.noMatches")}</p> : null}
      <CompactRegistryList>
        {filteredServers.map((server) => (
          <CatalogMcpRegistryItem
            key={server.id}
            server={server}
            backingToolName={toolNames.get(server.spec.backing_tool_id) ?? server.spec.backing_tool_id}
            validation={validationResults[server.id]?.validation}
            isValidating={validatingMcpServerId === server.id}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggle={onToggle}
            onValidate={onValidate}
            onViewDescription={setDescriptionServer}
            onViewLifecycle={openLifecycleItem}
          />
        ))}
      </CompactRegistryList>
      {descriptionServer ? (
        <CatalogMcpDescriptionModal server={descriptionServer} onClose={() => setDescriptionServer(null)} />
      ) : null}
      <LifecycleGraphActionModal
        item={selectedLifecycleItem}
        getTitle={(server) => t("catalogControl.mcp.lifecycle.modalTitle", { name: server.spec.name })}
        description={t("catalogControl.mcp.lifecycle.modalDescription")}
        closeLabel={t("actionFeedback.dialog.close")}
        definition={lifecycleDefinition}
        getCurrentState={getCatalogMcpLifecycleState}
        getSummaryRows={(server) => getCatalogMcpLifecycleSummaryRows(
          t,
          server,
          toolNames.get(server.spec.backing_tool_id) ?? server.spec.backing_tool_id,
        )}
        currentLabel={t("catalogControl.mcp.lifecycle.currentState")}
        unknownLabel={t("catalogControl.mcp.lifecycle.states.unknown")}
        onClose={closeLifecycleItem}
      />
    </article>
  );
}
