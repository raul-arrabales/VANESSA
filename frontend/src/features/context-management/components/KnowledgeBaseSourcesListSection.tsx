import { useTranslation } from "react-i18next";
import type { KnowledgeSource } from "../../../api/context";

type Props = {
  sources: KnowledgeSource[];
  isSuperadmin: boolean;
  syncingSourceId: string | null;
  onEdit: (source: KnowledgeSource) => void;
  onDelete: (sourceId: string) => Promise<void>;
  onSync: (sourceId: string) => Promise<void>;
};

export function KnowledgeBaseSourcesListSection({
  sources,
  isSuperadmin,
  syncingSourceId,
  onEdit,
  onDelete,
  onSync,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">{t("contextManagement.sourceViews.listTitle")}</h3>
          <p className="status-text">{t("contextManagement.sourceViews.listDescription")}</p>
        </div>
      </div>

      {sources.length === 0 ? <p className="status-text">{t("contextManagement.states.noSources")}</p> : null}
      {sources.map((source) => (
        <article key={source.id} className="panel card-stack">
          <div className="platform-card-header">
            <div className="card-stack">
              <h4 className="section-title">{source.display_name}</h4>
              <p className="status-text">{source.relative_path}</p>
            </div>
            <span className="status-chip status-chip-neutral">{`${source.lifecycle_state} / ${source.last_sync_status}`}</span>
          </div>
          {source.include_globs.length > 0 ? (
            <p className="status-text">
              {t("contextManagement.fields.includeGlobs")}: {source.include_globs.join(", ")}
            </p>
          ) : null}
          {source.exclude_globs.length > 0 ? (
            <p className="status-text">
              {t("contextManagement.fields.excludeGlobs")}: {source.exclude_globs.join(", ")}
            </p>
          ) : null}
          {source.last_sync_at ? (
            <p className="status-text">{t("contextManagement.fields.lastSourceSyncAt")}: {source.last_sync_at}</p>
          ) : null}
          {source.last_sync_error ? (
            <p className="status-text error-text">{t("contextManagement.fields.lastSyncError")}: {source.last_sync_error}</p>
          ) : null}
          {isSuperadmin ? (
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={syncingSourceId === source.id}
                onClick={() => void onSync(source.id)}
              >
                {syncingSourceId === source.id ? t("contextManagement.actions.syncingSource") : t("contextManagement.actions.syncSource")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => onEdit(source)}>
                {t("contextManagement.actions.edit")}
              </button>
              <button type="button" className="btn btn-danger" onClick={() => void onDelete(source.id)}>
                {t("contextManagement.actions.deleteSource")}
              </button>
            </div>
          ) : null}
        </article>
      ))}
    </section>
  );
}
