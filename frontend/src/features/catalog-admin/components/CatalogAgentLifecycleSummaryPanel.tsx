import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogAgent, CatalogAgentValidation } from "../../../api/catalog";
import { LifecycleGraphPanel } from "../../../components/LifecycleGraph";
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

  return (
    <LifecycleGraphPanel
      title={t("catalogControl.agents.lifecycle.title")}
      description={t("catalogControl.agents.lifecycle.summaryDescription")}
      definition={definition}
      items={agents}
      getState={(agent) => getCatalogAgentLifecycleState(agent, validationResults[agent.id])}
      currentLabel={t("catalogControl.agents.lifecycle.currentState")}
      unknownLabel={t("catalogControl.agents.lifecycle.states.unknown")}
    />
  );
}
