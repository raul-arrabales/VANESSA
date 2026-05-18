import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { LifecycleGraph, deriveLifecycleCounts } from "../../../components/LifecycleGraph";
import type { CatalogTool } from "../../../api/catalog";
import { createCatalogToolLifecycleGraphDefinition, getCatalogToolLifecycleState } from "../catalogToolLifecycleGraph";

type CatalogToolLifecycleSummaryPanelProps = {
  tools: CatalogTool[];
};

export default function CatalogToolLifecycleSummaryPanel({ tools }: CatalogToolLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createCatalogToolLifecycleGraphDefinition(t), [t]);
  const counts = useMemo(
    () => deriveLifecycleCounts(tools, definition, getCatalogToolLifecycleState),
    [definition, tools],
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.tools.lifecycle.title")}</h3>
        <p className="status-text">{t("catalogControl.tools.lifecycle.summaryDescription")}</p>
      </div>
      <LifecycleGraph
        definition={definition}
        counts={counts}
        currentLabel={t("catalogControl.tools.lifecycle.currentState")}
        unknownLabel={t("catalogControl.tools.lifecycle.states.unknown")}
      />
    </article>
  );
}
