import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogAgent, CatalogAgentValidation } from "../../../api/catalog";
import { LifecycleGraph, deriveLifecycleCounts } from "../../../components/LifecycleGraph";
import { createCatalogAgentLifecycleGraphDefinition, getCatalogAgentLifecycleState } from "../catalogAgentLifecycleGraph";

type CatalogAgentLifecycleSummaryPanelProps = {
  agents: CatalogAgent[];
  validationResults: Record<string, CatalogAgentValidation>;
};

export default function CatalogAgentLifecycleSummaryPanel({
  agents,
  validationResults,
}: CatalogAgentLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createCatalogAgentLifecycleGraphDefinition(t), [t]);
  const counts = useMemo(
    () => deriveLifecycleCounts(agents, definition, (agent) => getCatalogAgentLifecycleState(agent, validationResults[agent.id])),
    [agents, definition, validationResults],
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.agents.lifecycle.title")}</h3>
        <p className="status-text">{t("catalogControl.agents.lifecycle.summaryDescription")}</p>
      </div>
      <LifecycleGraph
        definition={definition}
        counts={counts}
        currentLabel={t("catalogControl.agents.lifecycle.currentState")}
        unknownLabel={t("catalogControl.agents.lifecycle.states.unknown")}
      />
    </article>
  );
}
