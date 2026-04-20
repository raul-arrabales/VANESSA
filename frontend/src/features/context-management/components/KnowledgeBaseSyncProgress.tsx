import { useTranslation } from "react-i18next";
import type { KnowledgeSyncRun } from "../../../api/context";

type Props = {
  run: KnowledgeSyncRun;
};

export function KnowledgeBaseSyncProgress({ run }: Props): JSX.Element {
  const { t } = useTranslation("common");
  const progress = typeof run.progress_percent === "number" ? Math.max(0, Math.min(100, run.progress_percent)) : null;
  const isDeterminate = progress !== null;
  const label = run.current_step || t("contextManagement.syncProgress.queued");

  return (
    <div className="context-sync-progress card-stack">
      <div className="status-row">
        <span className="status-text">{label}</span>
        <span className="status-text">
          {isDeterminate ? t("contextManagement.syncProgress.percent", { percent: progress }) : run.status}
        </span>
      </div>
      <div
        className="context-sync-progress-track"
        data-mode={isDeterminate ? "determinate" : "indeterminate"}
        role="progressbar"
        aria-label={t("contextManagement.syncProgress.aria")}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={isDeterminate ? progress : undefined}
      >
        <div
          className="context-sync-progress-bar"
          style={isDeterminate ? { width: `${progress}%` } : undefined}
        />
      </div>
      {run.current_path ? (
        <p className="status-text context-sync-progress-path">{run.current_path}</p>
      ) : null}
    </div>
  );
}
