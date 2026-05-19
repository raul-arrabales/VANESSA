import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer } from "../../../api/catalog";
import { LifecycleGraphPanel } from "../../../components/LifecycleGraph";
import { createCatalogMcpLifecycleGraphDefinition, getCatalogMcpLifecycleState } from "../catalogMcpLifecycleGraph";

type CatalogMcpLifecycleSummaryPanelProps = {
  mcpServers: CatalogMcpServer[];
};

export default function CatalogMcpLifecycleSummaryPanel({ mcpServers }: CatalogMcpLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createCatalogMcpLifecycleGraphDefinition(t), [t]);

  return (
    <LifecycleGraphPanel
      title={t("catalogControl.mcp.lifecycle.title")}
      description={t("catalogControl.mcp.lifecycle.summaryDescription")}
      definition={definition}
      items={mcpServers}
      getState={getCatalogMcpLifecycleState}
      currentLabel={t("catalogControl.mcp.lifecycle.currentState")}
      unknownLabel={t("catalogControl.mcp.lifecycle.states.unknown")}
    />
  );
}
