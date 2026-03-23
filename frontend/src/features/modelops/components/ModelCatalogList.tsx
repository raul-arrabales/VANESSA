import { Link } from "react-router-dom";
import type { ManagedModel } from "../../../api/modelops/types";
import { isModelTestEligible } from "../domain";
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
    <ul className="card-stack" aria-label="Model catalog list">
      {models.map((model) => {
        const isCurrentlyValidated =
          model.is_validation_current === true && model.last_validation_status === "success";

        return (
          <li key={model.id} className="panel card-stack">
            <div className="modelops-card-header">
              <div className="card-stack">
                <strong>{model.name}</strong>
                <span className="status-text">{model.id}</span>
              </div>
              <div className="button-row">
                <ModelStatusBadge
                  label={model.lifecycle_state ?? "unknown"}
                  tone={model.lifecycle_state === "active" ? "success" : "neutral"}
                />
                <ModelStatusBadge
                  label={model.hosting ?? (model.backend === "local" ? "local" : "cloud")}
                  tone={model.backend === "local" ? "warning" : "neutral"}
                />
                <ModelStatusBadge
                  label={isCurrentlyValidated ? validatedLabel : notValidatedLabel}
                  tone={isCurrentlyValidated ? "success" : "warning"}
                />
              </div>
            </div>
            <p className="status-text">
              {model.task_key ?? "unknown"} · {model.provider} · {model.owner_type ?? "unknown"} · {model.visibility_scope ?? "private"}
            </p>
            <p className="status-text">
              Validation: {model.last_validation_status ?? "pending"} · Current: {model.is_validation_current ? "yes" : "no"}
            </p>
            <div className="button-row">
              {canTest && isModelTestEligible(model) && (
                <Link className="btn btn-primary" to={`/control/models/${encodeURIComponent(model.id)}/test`}>
                  {testLabel ?? "Test"}
                </Link>
              )}
              <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(model.id)}`}>
                {detailLabel}
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
