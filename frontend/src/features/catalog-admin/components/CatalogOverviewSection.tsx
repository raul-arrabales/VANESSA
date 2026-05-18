import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { OptionCardItem } from "../../../components/OptionCardGrid";
import OptionCardGrid from "../../../components/OptionCardGrid";
import type { CatalogMcpServer, CatalogTool } from "../../../api/catalog";
import type { CatalogLoadState } from "../hooks/useCatalogControl";
import { buildCatalogControlUrl } from "../routes";
import CatalogMcpLifecycleSummaryPanel from "./CatalogMcpLifecycleSummaryPanel";
import CatalogToolLifecycleSummaryPanel from "./CatalogToolLifecycleSummaryPanel";

type CatalogOverviewSectionProps = {
  state: CatalogLoadState;
  agentCount: number;
  publishedAgents: number;
  toolCount: number;
  publishedTools: number;
  tools: CatalogTool[];
  mcpServers: CatalogMcpServer[];
  mcpServerCount: number;
  enabledMcpServers: number;
  modelCount: number;
};

export default function CatalogOverviewSection({
  state,
  agentCount,
  publishedAgents,
  toolCount,
  publishedTools,
  tools,
  mcpServers,
  mcpServerCount,
  enabledMcpServers,
  modelCount,
}: CatalogOverviewSectionProps): JSX.Element {
  const { t } = useTranslation("common");
  const entryCards = useMemo((): OptionCardItem[] => [
    {
      id: "tools",
      title: t("catalogControl.home.toolsTitle"),
      description: t("catalogControl.home.toolsDescription"),
      to: buildCatalogControlUrl("tools", "tools"),
      icon: "settings",
    },
    {
      id: "mcp",
      title: t("catalogControl.home.mcpTitle"),
      description: t("catalogControl.home.mcpDescription"),
      to: buildCatalogControlUrl("mcp", "registry"),
      icon: "settings",
    },
    {
      id: "agents",
      title: t("catalogControl.home.agentsTitle"),
      description: t("catalogControl.home.agentsDescription"),
      to: buildCatalogControlUrl("agents", "agents"),
      icon: "models",
    },
  ], [t]);

  return (
    <>
      <article className="panel card-stack">
        <div className="summary-card-grid">
          <div className="summary-card">
            <span className="field-label">{t("catalogControl.summary.agents")}</span>
            <strong>{agentCount}</strong>
            <span className="status-text">{t("catalogControl.summary.publishedCount", { count: publishedAgents })}</span>
          </div>
          <div className="summary-card">
            <span className="field-label">{t("catalogControl.summary.tools")}</span>
            <strong>{toolCount}</strong>
            <span className="status-text">{t("catalogControl.summary.publishedCount", { count: publishedTools })}</span>
          </div>
          <div className="summary-card">
            <span className="field-label">{t("catalogControl.summary.models")}</span>
            <strong>{modelCount}</strong>
            <span className="status-text">{t(`catalogControl.state.${state}`)}</span>
          </div>
          <div className="summary-card">
            <span className="field-label">{t("catalogControl.summary.mcpServers")}</span>
            <strong>{mcpServerCount}</strong>
            <span className="status-text">{t("catalogControl.summary.enabledCount", { count: enabledMcpServers })}</span>
          </div>
        </div>
      </article>

      <CatalogToolLifecycleSummaryPanel tools={tools} />
      <CatalogMcpLifecycleSummaryPanel mcpServers={mcpServers} />

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("catalogControl.home.exploreTitle")}</h3>
          <p className="status-text">{t("catalogControl.home.exploreDescription")}</p>
        </div>
        <OptionCardGrid items={entryCards} ariaLabel={t("catalogControl.home.exploreAria")} />
      </article>
    </>
  );
}
