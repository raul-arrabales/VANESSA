import { Link } from "react-router-dom";
import type { LocalModelArtifact } from "../../../api/modelops/types";
import { useTranslation } from "react-i18next";

type LocalArtifactListProps = {
  artifacts: LocalModelArtifact[];
  registeringArtifactId: string;
  onRegister: (artifact: LocalModelArtifact) => Promise<void>;
};

export default function LocalArtifactList({
  artifacts,
  registeringArtifactId,
  onRegister,
}: LocalArtifactListProps): JSX.Element {
  const { t } = useTranslation("common");

  if (artifacts.length === 0) {
    return <p className="status-text">{t("modelOps.local.noArtifacts")}</p>;
  }

  return (
    <ul className="card-stack" aria-label="Local artifact list">
      {artifacts.map((artifact) => (
        <li key={artifact.artifact_id} className="panel card-stack">
          <div className="modelops-card-header">
            <div className="card-stack">
              <strong>{artifact.name ?? artifact.suggested_model_id ?? artifact.artifact_id}</strong>
              <span className="status-text">{artifact.storage_path ?? artifact.source_id ?? artifact.artifact_id}</span>
            </div>
            <span className="status-chip status-chip-neutral">{artifact.artifact_status ?? "unknown"}</span>
          </div>
          <p className="status-text">
            {artifact.task_key ?? "unknown"} · {artifact.lifecycle_state ?? "unknown"} · {artifact.validation_hint ?? "unknown"}
          </p>
          <div className="button-row">
            {artifact.linked_model_id && (
              <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(artifact.linked_model_id)}`}>
                {t("modelOps.actions.openDetail")}
              </Link>
            )}
            {artifact.ready_for_registration && artifact.suggested_model_id && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={registeringArtifactId === artifact.artifact_id}
                onClick={() => void onRegister(artifact)}
              >
                {t("modelOps.actions.register")}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
