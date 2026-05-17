import { Link } from "react-router-dom";
import type { ManagedModel } from "../../../api/modelops/types";
import { isModelTestEligible } from "../domain";
import ModelCatalogActionIcon from "./ModelCatalogActionIcon";
import ModelStatusBadge from "./ModelStatusBadge";

type ModelCatalogListProps = {
  models: ManagedModel[];
  emptyLabel: string;
  detailLabel: string;
  testLabel?: string;
  validatedLabel: string;
  notValidatedLabel: string;
  canTest?: boolean;
};

export default function ModelCatalogList({
  models,
  emptyLabel,
  detailLabel,
  testLabel,
  validatedLabel,
  notValidatedLabel,
  canTest = false,
}: ModelCatalogListProps): JSX.Element {
  if (models.length === 0) {
    return <p className="status-text">{emptyLabel}</p>;
  }

  return (
    <ul className="modelops-catalog-list" aria-label="Model catalog list">
      {models.map((model) => {
        const isCurrentlyValidated =
          model.is_validation_current === true && model.last_validation_status === "success";
        const hosting = model.hosting ?? (model.backend === "local" ? "local" : "cloud");
        const detailActionLabel = `${detailLabel}: ${model.name}`;
        const testActionLabel = `${testLabel ?? "Test"}: ${model.name}`;

        return (
          <li key={model.id} className="modelops-catalog-item">
            <div className="modelops-catalog-main">
              <div className="modelops-catalog-heading">
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
              </div>
              <div className="modelops-catalog-meta-row">
                <code className="code-inline">{model.id}</code>
                <span>{model.task_key ?? "unknown"}</span>
                <span>{model.provider}</span>
                <span>{model.owner_type ?? "unknown"}</span>
                <span>{model.visibility_scope ?? "private"}</span>
                <span>Validation: {model.last_validation_status ?? "pending"} · Current: {model.is_validation_current ? "yes" : "no"}</span>
              </div>
            </div>
            <div className="modelops-catalog-actions" role="group" aria-label={`Model actions for ${model.name}`}>
              {canTest && isModelTestEligible(model) && (
                <Link
                  className="icon-button"
                  to={`/control/models/${encodeURIComponent(model.id)}/test`}
                  aria-label={testActionLabel}
                  title={testActionLabel}
                >
                  <ModelCatalogActionIcon name="test" />
                </Link>
              )}
              <Link
                className="icon-button"
                to={`/control/models/${encodeURIComponent(model.id)}`}
                aria-label={detailActionLabel}
                title={detailActionLabel}
              >
                <ModelCatalogActionIcon name="details" />
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
