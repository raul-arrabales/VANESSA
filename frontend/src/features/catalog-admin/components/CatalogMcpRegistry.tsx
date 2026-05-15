import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer, CatalogMcpServerValidation, CatalogTool } from "../../../api/catalog";
import CatalogMcpDescriptionModal from "./CatalogMcpDescriptionModal";
import CatalogMcpRegistryItem from "./CatalogMcpRegistryItem";

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
          />
        ))}
      </div>
      {descriptionServer ? (
        <CatalogMcpDescriptionModal server={descriptionServer} onClose={() => setDescriptionServer(null)} />
      ) : null}
    </article>
  );
}
