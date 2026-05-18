import type { LocalModelArtifact } from "../../../api/modelops/types";
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
import IconButton from "../../../components/IconButton";
import IconLink from "../../../components/IconLink";

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
    <CompactRegistryList ariaLabel={t("modelOps.artifacts.listAria")}>
      {artifacts.map((artifact) => {
        const displayName = artifact.name ?? artifact.suggested_model_id ?? artifact.artifact_id;
        const isRegistering = registeringArtifactId === artifact.artifact_id;
        const detailLabel = t("modelOps.artifacts.actionLabels.openDetail", { name: displayName });
        const registerLabel = isRegistering
          ? t("modelOps.artifacts.actionLabels.registering", { name: displayName })
          : t("modelOps.artifacts.actionLabels.register", { name: displayName });

        return (
          <CompactRegistryItem key={artifact.artifact_id}>
            <CompactRegistryMain>
              <CompactRegistryHeading>
                <h3 className="section-title">{displayName}</h3>
                <span className="status-chip status-chip-neutral">{artifact.artifact_status ?? "unknown"}</span>
                <span className="status-chip status-chip-neutral">{artifact.lifecycle_state ?? "unknown"}</span>
                <span className={`status-chip ${artifact.ready_for_registration ? "status-chip-success" : "status-chip-warning"}`}>
                  {artifact.ready_for_registration ? t("modelOps.artifacts.ready") : t("modelOps.artifacts.notReady")}
                </span>
              </CompactRegistryHeading>
              <CompactRegistryMeta>
                <code className="code-inline">{artifact.artifact_id}</code>
                <span>{artifact.storage_path ?? artifact.source_id ?? "-"}</span>
                <span>{artifact.task_key ?? "unknown"}</span>
                <span>{artifact.validation_hint ?? "unknown"}</span>
                {artifact.suggested_model_id ? <span>{artifact.suggested_model_id}</span> : null}
              </CompactRegistryMeta>
            </CompactRegistryMain>
            <CompactRegistryActions label={t("modelOps.artifacts.actionsFor", { name: displayName })}>
              {artifact.linked_model_id ? (
                <IconLink
                  to={`/control/models/${encodeURIComponent(artifact.linked_model_id)}`}
                  label={detailLabel}
                >
                  <ActionIcon name="details" />
                </IconLink>
              ) : null}
              {artifact.ready_for_registration && artifact.suggested_model_id ? (
                <IconButton label={registerLabel} disabled={isRegistering} onClick={() => void onRegister(artifact)}>
                  <ActionIcon name="register" />
                </IconButton>
              ) : null}
            </CompactRegistryActions>
          </CompactRegistryItem>
        );
      })}
    </CompactRegistryList>
  );
}
