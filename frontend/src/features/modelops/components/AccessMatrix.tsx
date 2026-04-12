import { useTranslation } from "react-i18next";
import type { ManagedModelLifecycleState, ManagedModelTaskKey } from "../../../api/modelops/types";
import type { ManagedModel } from "../../../api/modelops/types";
import ModelStatusBadge from "./ModelStatusBadge";

type BadgeTone = "neutral" | "success" | "warning" | "info" | "danger";

function getTaskTone(taskKey?: ManagedModelTaskKey | null): BadgeTone {
  switch (taskKey) {
    case "llm":
      return "info";
    case "embeddings":
      return "warning";
    case "translation":
      return "success";
    case "classification":
      return "neutral";
    default:
      return "neutral";
  }
}

function getLifecycleTone(lifecycleState?: ManagedModelLifecycleState | null): BadgeTone {
  switch (lifecycleState) {
    case "active":
    case "validated":
      return "success";
    case "registered":
      return "info";
    case "created":
    case "inactive":
    case "unregistered":
      return "warning";
    case "deleted":
      return "danger";
    default:
      return "neutral";
  }
}

type AccessMatrixProps = {
  scopes: readonly string[];
  models: ManagedModel[];
  assignmentByScope: Map<string, string[]>;
  onToggle: (scope: string, modelId: string) => Promise<void>;
  highlightedModelId?: string;
};

export default function AccessMatrix({
  scopes,
  models,
  assignmentByScope,
  onToggle,
  highlightedModelId,
}: AccessMatrixProps): JSX.Element {
  const { t } = useTranslation("common");

  const getScopeLabel = (scope: string): string => t(`modelOps.access.scopes.${scope}`);

  if (models.length === 0) {
    return <p className="status-text">{t("modelOps.access.empty")}</p>;
  }

  return (
    <div className="health-table-wrap">
      <table className="health-table modelops-access-table" aria-label={t("modelOps.access.tableAria")}>
        <thead>
          <tr>
            <th scope="col">{t("modelOps.access.columns.model")}</th>
            {scopes.map((scope) => (
              <th key={scope} scope="col">{getScopeLabel(scope)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {models.map((model) => {
            const isHighlighted = highlightedModelId === model.id;
            return (
              <tr key={model.id} className={isHighlighted ? "is-highlighted" : undefined}>
                <th scope="row">
                  <strong>{model.name}</strong>
                  <div className="inline-meta-list">
                    <span className="status-text">{model.id}</span>
                    <ModelStatusBadge label={model.task_key ?? "unknown"} tone={getTaskTone(model.task_key)} />
                    <ModelStatusBadge
                      label={model.lifecycle_state ?? "unknown"}
                      tone={getLifecycleTone(model.lifecycle_state)}
                    />
                  </div>
                </th>
                {scopes.map((scope) => {
                  const scopeLabel = getScopeLabel(scope);
                  const checked = (assignmentByScope.get(scope) ?? []).includes(model.id);
                  return (
                    <td key={`${model.id}-${scope}`}>
                      <label className="modelops-access-toggle">
                        <input
                          type="checkbox"
                          checked={checked}
                          aria-label={t("modelOps.access.toggleLabel", { model: model.name, scope: scopeLabel })}
                          onChange={() => void onToggle(scope, model.id)}
                        />
                      </label>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
