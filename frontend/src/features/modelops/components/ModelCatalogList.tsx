import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ActionIcon from "../../../components/ActionIcon";
import {
  CompactRegistryActions,
  CompactRegistryHeading,
  CompactRegistryItem,
  CompactRegistryList,
  CompactRegistryMain,
  CompactRegistryMeta,
} from "../../../components/CompactRegistryList";
import IconLink from "../../../components/IconLink";
import IconButton from "../../../components/IconButton";
import { LifecycleGraphModal } from "../../../components/LifecycleGraph";
import type { ManagedModel } from "../../../api/modelops/types";
import { isModelTestEligible } from "../domain";
import { createModelLifecycleGraphDefinition, getModelLifecycleState, getModelValidationLifecycleSummary } from "../modelLifecycleGraph";
import ModelStatusBadge from "./ModelStatusBadge";

type ModelCatalogListProps = {
  models: ManagedModel[];
  emptyLabel: string;
  validatedLabel: string;
  notValidatedLabel: string;
  canTest?: boolean;
};

export default function ModelCatalogList({
  models,
  emptyLabel,
  validatedLabel,
  notValidatedLabel,
  canTest = false,
}: ModelCatalogListProps): JSX.Element {
  const { t } = useTranslation("common");
  const [selectedLifecycleModel, setSelectedLifecycleModel] = useState<ManagedModel | null>(null);
  const lifecycleDefinition = useMemo(() => createModelLifecycleGraphDefinition(t), [t]);

  if (models.length === 0) {
    return <p className="status-text">{emptyLabel}</p>;
  }

  return (
    <>
      <CompactRegistryList ariaLabel={t("modelOps.catalog.listAria")}>
        {models.map((model) => {
          const isCurrentlyValidated =
            model.is_validation_current === true && model.last_validation_status === "success";
          const hosting = model.hosting ?? (model.backend === "local" ? "local" : "cloud");
          const detailActionLabel = t("modelOps.catalog.actionLabels.openDetail", { name: model.name });
          const testActionLabel = t("modelOps.catalog.actionLabels.testModel", { name: model.name });
          const lifecycleActionLabel = t("modelOps.catalog.actionLabels.lifecycle", { name: model.name });

          return (
            <CompactRegistryItem key={model.id}>
              <CompactRegistryMain>
                <CompactRegistryHeading>
                  <h3 className="section-title">{model.name}</h3>
                  <ModelStatusBadge
                    label={model.lifecycle_state ?? "unknown"}
                    tone={model.lifecycle_state === "active" ? "success" : "neutral"}
                  />
                  <ModelStatusBadge
                    label={hosting}
                    tone={model.backend === "local" ? "warning" : "neutral"}
                  />
                  <ModelStatusBadge
                    label={isCurrentlyValidated ? validatedLabel : notValidatedLabel}
                    tone={isCurrentlyValidated ? "success" : "warning"}
                  />
                </CompactRegistryHeading>
                <CompactRegistryMeta>
                  <code className="code-inline">{model.id}</code>
                  <span>{model.task_key ?? "unknown"}</span>
                  <span>{model.provider}</span>
                  <span>{model.owner_type ?? "unknown"}</span>
                  <span>{model.visibility_scope ?? "private"}</span>
                  <span>Validation: {model.last_validation_status ?? "pending"} · Current: {model.is_validation_current ? "yes" : "no"}</span>
                </CompactRegistryMeta>
              </CompactRegistryMain>
              <CompactRegistryActions label={t("modelOps.catalog.actionsFor", { name: model.name })}>
                <IconButton label={lifecycleActionLabel} onClick={() => setSelectedLifecycleModel(model)}>
                  <ActionIcon name="lifecycle" />
                </IconButton>
                {canTest && isModelTestEligible(model) && (
                  <IconLink
                    to={`/control/models/${encodeURIComponent(model.id)}/test`}
                    label={testActionLabel}
                  >
                    <ActionIcon name="test" />
                  </IconLink>
                )}
                <IconLink
                  to={`/control/models/${encodeURIComponent(model.id)}`}
                  label={detailActionLabel}
                >
                  <ActionIcon name="details" />
                </IconLink>
              </CompactRegistryActions>
            </CompactRegistryItem>
          );
        })}
      </CompactRegistryList>
      {selectedLifecycleModel ? (
        <LifecycleGraphModal
          title={t("modelOps.lifecycle.modalTitle", { name: selectedLifecycleModel.name })}
          description={t("modelOps.lifecycle.modalDescription")}
          closeLabel={t("actionFeedback.dialog.close")}
          definition={lifecycleDefinition}
          currentState={getModelLifecycleState(selectedLifecycleModel)}
          supportingText={getModelValidationLifecycleSummary(t, selectedLifecycleModel)}
          currentLabel={t("modelOps.lifecycle.currentState")}
          unknownLabel={t("modelOps.lifecycle.states.unknown")}
          onClose={() => setSelectedLifecycleModel(null)}
        />
      ) : null}
    </>
  );
}
