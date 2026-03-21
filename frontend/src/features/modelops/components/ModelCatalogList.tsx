import { Link } from "react-router-dom";
import type { ManagedModel } from "../../../api/models";
import ModelStatusBadge from "./ModelStatusBadge";

type ModelCatalogListProps = {
  models: ManagedModel[];
  emptyLabel: string;
  detailLabel: string;
  testLabel?: string;
  canTest?: boolean;
};

function isModelTestEligible(model: ManagedModel): boolean {
  return ["registered", "validated", "inactive", "active"].includes(String(model.lifecycle_state ?? "").toLowerCase());
}

export default function ModelCatalogList({
  models,
  emptyLabel,
  detailLabel,
  testLabel,
  canTest = false,
}: ModelCatalogListProps): JSX.Element {
  if (models.length === 0) {
    return <p className="status-text">{emptyLabel}</p>;
  }

  return (
    <ul className="card-stack" aria-label="Model catalog list">
      {models.map((model) => (
        <li key={model.id} className="panel card-stack">
          <div className="modelops-card-header">
            <div className="card-stack">
              <strong>{model.name}</strong>
              <span className="status-text">{model.id}</span>
            </div>
            <div className="button-row">
              <ModelStatusBadge label={model.lifecycle_state ?? "unknown"} tone={model.lifecycle_state === "active" ? "success" : "neutral"} />
              <ModelStatusBadge
                label={model.hosting ?? (model.backend === "local" ? "local" : "cloud")}
                tone={model.backend === "local" ? "warning" : "neutral"}
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
      ))}
    </ul>
  );
}
