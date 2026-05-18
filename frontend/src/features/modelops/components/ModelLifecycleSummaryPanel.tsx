import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops/types";
import { LifecycleGraph, deriveLifecycleCounts } from "../../../components/LifecycleGraph";
import { createModelLifecycleGraphDefinition, getModelLifecycleState } from "../modelLifecycleGraph";

type ModelLifecycleSummaryPanelProps = {
  models: ManagedModel[];
};

export default function ModelLifecycleSummaryPanel({
  models,
}: ModelLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createModelLifecycleGraphDefinition(t), [t]);
  const counts = useMemo(
    () => deriveLifecycleCounts(models, definition, getModelLifecycleState),
    [definition, models],
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h2 className="section-title">{t("modelOps.lifecycle.title")}</h2>
        <p className="status-text">{t("modelOps.lifecycle.summaryDescription")}</p>
      </div>
      <LifecycleGraph
        definition={definition}
        counts={counts}
        currentLabel={t("modelOps.lifecycle.currentState")}
        unknownLabel={t("modelOps.lifecycle.states.unknown")}
      />
    </article>
  );
}
