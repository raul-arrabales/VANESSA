import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { LifecycleGraphPanel } from "../../../components/LifecycleGraph";
import type { CatalogTool } from "../../../api/catalog";
import { createCatalogToolLifecycleGraphDefinition, getCatalogToolLifecycleState } from "../catalogToolLifecycleGraph";

type CatalogToolLifecycleSummaryPanelProps = {
  tools: CatalogTool[];
};

export default function CatalogToolLifecycleSummaryPanel({ tools }: CatalogToolLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createCatalogToolLifecycleGraphDefinition(t), [t]);

  return (
    <LifecycleGraphPanel
      title={t("catalogControl.tools.lifecycle.title")}
      description={t("catalogControl.tools.lifecycle.summaryDescription")}
      definition={definition}
      items={tools}
      getState={getCatalogToolLifecycleState}
      currentLabel={t("catalogControl.tools.lifecycle.currentState")}
      unknownLabel={t("catalogControl.tools.lifecycle.states.unknown")}
    />
  );
}
