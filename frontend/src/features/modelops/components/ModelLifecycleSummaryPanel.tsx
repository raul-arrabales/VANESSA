import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { ManagedModel } from "../../../api/modelops/types";
import { LifecycleGraphPanel } from "../../../components/LifecycleGraph";
import { createModelLifecycleGraphDefinition, getModelLifecycleState } from "../modelLifecycleGraph";

type ModelLifecycleSummaryPanelProps = {
  models: ManagedModel[];
};

export default function ModelLifecycleSummaryPanel({
  models,
}: ModelLifecycleSummaryPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const definition = useMemo(() => createModelLifecycleGraphDefinition(t), [t]);

  return (
    <LifecycleGraphPanel
      title={t("modelOps.lifecycle.title")}
      description={t("modelOps.lifecycle.summaryDescription")}
      definition={definition}
      items={models}
      getState={getModelLifecycleState}
      currentLabel={t("modelOps.lifecycle.currentState")}
      unknownLabel={t("modelOps.lifecycle.states.unknown")}
      titleAs="h2"
    />
  );
}
