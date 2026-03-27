import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeSource } from "../../../api/context";
import { EMPTY_SOURCE_FORM, type SourceFormState } from "../types";

type Props = {
  sources: KnowledgeSource[];
  sourceForm: SourceFormState;
  isSuperadmin: boolean;
  syncingSourceId: string | null;
  onSourceFormChange: Dispatch<SetStateAction<SourceFormState>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onDelete: (sourceId: string) => Promise<void>;
  onSync: (sourceId: string) => Promise<void>;
};

export function KnowledgeBaseSourcesSection({
  sources,
  sourceForm,
  isSuperadmin,
  syncingSourceId,
  onSourceFormChange,
  onSubmit,
  onDelete,
  onSync,
}: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">{t("contextManagement.sourcesTitle")}</h3>
          <p className="status-text">{t("contextManagement.sourcesDescription")}</p>
          <p className="status-text">{t("contextManagement.states.supportedFileTypes")}</p>
        </div>
      </div>

      {isSuperadmin ? (
        <form className="card-stack" onSubmit={(event) => void onSubmit(event)}>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.sourceDisplayName")}</span>
            <input
              className="field-input"
              value={sourceForm.displayName}
              onChange={(event) => onSourceFormChange((current) => ({ ...current, displayName: event.currentTarget.value }))}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.sourceRelativePath")}</span>
            <input
              className="field-input"
              value={sourceForm.relativePath}
              onChange={(event) => onSourceFormChange((current) => ({ ...current, relativePath: event.currentTarget.value }))}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.includeGlobs")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={sourceForm.includeGlobs}
              onChange={(event) => onSourceFormChange((current) => ({ ...current, includeGlobs: event.currentTarget.value }))}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.excludeGlobs")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={sourceForm.excludeGlobs}
              onChange={(event) => onSourceFormChange((current) => ({ ...current, excludeGlobs: event.currentTarget.value }))}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.lifecycleState")}</span>
            <select
              className="field-input"
              value={sourceForm.lifecycleState}
              onChange={(event) => onSourceFormChange((current) => ({ ...current, lifecycleState: event.currentTarget.value }))}
            >
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              {sourceForm.id ? t("contextManagement.actions.updateSource") : t("contextManagement.actions.addSource")}
            </button>
            {sourceForm.id ? (
              <button type="button" className="btn btn-secondary" onClick={() => onSourceFormChange(EMPTY_SOURCE_FORM)}>
                {t("platformControl.actions.cancel")}
              </button>
            ) : null}
          </div>
        </form>
      ) : null}

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
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() =>
                  onSourceFormChange({
                    id: source.id,
                    displayName: source.display_name,
                    relativePath: source.relative_path,
                    includeGlobs: source.include_globs.join("\n"),
                    excludeGlobs: source.exclude_globs.join("\n"),
                    lifecycleState: source.lifecycle_state,
                  })
                }
              >
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
