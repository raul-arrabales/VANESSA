import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer } from "../../../api/catalog";
import { LifecycleGraph, deriveLifecycleCounts } from "../../../components/LifecycleGraph";
import { createCatalogMcpLifecycleGraphDefinition, getCatalogMcpLifecycleState } from "../catalogMcpLifecycleGraph";

type CatalogMcpLifecycleSummaryPanelProps = {
  mcpServers: CatalogMcpServer[];
};

export default function CatalogMcpLifecycleSummaryPanel({ mcpServers }: CatalogMcpLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createCatalogMcpLifecycleGraphDefinition(t), [t]);
  const counts = useMemo(
    () => deriveLifecycleCounts(mcpServers, definition, getCatalogMcpLifecycleState),
    [definition, mcpServers],
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.mcp.lifecycle.title")}</h3>
        <p className="status-text">{t("catalogControl.mcp.lifecycle.summaryDescription")}</p>
      </div>
      <LifecycleGraph
        definition={definition}
        counts={counts}
        currentLabel={t("catalogControl.mcp.lifecycle.currentState")}
        unknownLabel={t("catalogControl.mcp.lifecycle.states.unknown")}
      />
    </article>
  );
}
