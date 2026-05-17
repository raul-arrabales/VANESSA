import { useTranslation } from "react-i18next";
import IconButton from "../../../components/IconButton";
import type { KnowledgeSource, KnowledgeSyncRun } from "../../../api/context";
import ContextActionIcon from "./ContextActionIcon";
import { KnowledgeBaseSyncProgress } from "./KnowledgeBaseSyncProgress";

type Props = {
  sources: KnowledgeSource[];
  isSuperadmin: boolean;
  syncingSourceId: string | null;
  activeSyncRuns: KnowledgeSyncRun[];
  onEdit: (source: KnowledgeSource) => void;
  onDelete: (sourceId: string) => Promise<void>;
  onSync: (sourceId: string) => Promise<void>;
};

export function KnowledgeBaseSourcesListSection({
  sources,
  isSuperadmin,
  syncingSourceId,
  activeSyncRuns,
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
      <div className="context-compact-list" role="list">
        {sources.map((source) => {
          const activeRun = activeSyncRuns.find((run) => run.source_id === source.id) ?? null;
          const isSourceSyncing = syncingSourceId === source.id || activeRun !== null;

          return (
            <article key={source.id} className="context-compact-list-item" role="listitem">
              <div className="context-compact-list-main">
                <div className="context-compact-list-heading">
                  <h4 className="section-title">{source.display_name}</h4>
                  <span className="status-chip status-chip-neutral">{source.lifecycle_state}</span>
                  <span className={`status-chip ${source.last_sync_status === "error" ? "status-chip-danger" : "status-chip-neutral"}`}>
                    {source.last_sync_status}
                  </span>
                </div>
                <div className="context-compact-meta-row">
                  <code className="code-inline">{source.id}</code>
                  <span>{source.relative_path}</span>
                  {source.include_globs.length > 0 ? <span>{t("contextManagement.fields.includeGlobs")}: {source.include_globs.join(", ")}</span> : null}
                  {source.exclude_globs.length > 0 ? <span>{t("contextManagement.fields.excludeGlobs")}: {source.exclude_globs.join(", ")}</span> : null}
                  {source.last_sync_at ? <span>{t("contextManagement.fields.lastSourceSyncAt")}: {source.last_sync_at}</span> : null}
                  {source.last_sync_error ? <span className="error-text">{t("contextManagement.fields.lastSyncError")}: {source.last_sync_error}</span> : null}
                </div>
              </div>
              {isSuperadmin ? (
                <div className="context-compact-actions" role="group" aria-label={t("contextManagement.actionLabels.sourceActionsFor", { name: source.display_name })}>
                  <IconButton
                    label={isSourceSyncing
                      ? t("contextManagement.actionLabels.syncingSource", { name: source.display_name })
                      : t("contextManagement.actionLabels.syncSource", { name: source.display_name })}
                    disabled={isSourceSyncing}
                    onClick={() => void onSync(source.id)}
                  >
                    <ContextActionIcon name="sync" />
                  </IconButton>
                  <IconButton label={t("contextManagement.actionLabels.editSource", { name: source.display_name })} onClick={() => onEdit(source)}>
                    <ContextActionIcon name="edit" />
                  </IconButton>
                  <IconButton label={t("contextManagement.actionLabels.deleteSource", { name: source.display_name })} tone="danger" onClick={() => void onDelete(source.id)}>
                    <ContextActionIcon name="delete" />
                  </IconButton>
                </div>
              ) : null}
              {activeRun ? (
                <div className="context-compact-progress">
                  <KnowledgeBaseSyncProgress run={activeRun} />
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
