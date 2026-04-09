import { useTranslation } from "react-i18next";
import type { KnowledgeSyncRun } from "../../../api/context";

type Props = {
  syncRuns: KnowledgeSyncRun[];
};

export function KnowledgeBaseSyncHistorySection({ syncRuns }: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">{t("contextManagement.syncHistoryTitle")}</h3>
          <p className="status-text">{t("contextManagement.syncHistoryDescription")}</p>
        </div>
      </div>
      {syncRuns.length === 0 ? <p className="status-text">{t("contextManagement.states.noSyncRuns")}</p> : null}
      {syncRuns.map((run) => (
        <article key={run.id} className="panel panel-nested card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h4 className="section-title">{run.source_display_name || t("contextManagement.states.fullKnowledgeBaseResync")}</h4>
              <p className="status-text">{run.started_at}</p>
            </div>
            <span className="status-chip status-chip-neutral">{run.status}</span>
          </div>
          <p className="status-text">
            {t("contextManagement.states.syncRunSummary", {
              scanned: run.scanned_file_count,
              changed: run.changed_file_count,
              deletedFiles: run.deleted_file_count,
              createdDocs: run.created_document_count,
              updatedDocs: run.updated_document_count,
              deletedDocs: run.deleted_document_count,
            })}
          </p>
          {run.error_summary ? <p className="status-text error-text">{run.error_summary}</p> : null}
        </article>
      ))}
    </section>
  );
}
