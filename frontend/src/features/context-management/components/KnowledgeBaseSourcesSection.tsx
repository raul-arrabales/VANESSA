import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeSource, KnowledgeSourceDirectoriesResponse } from "../../../api/context";
import { createEmptySourceForm, type SourceFormState } from "../types";

type Props = {
  sources: KnowledgeSource[];
  sourceForm: SourceFormState;
  sourceDirectoryBrowser: {
    open: boolean;
    loading: boolean;
    payload: KnowledgeSourceDirectoriesResponse | null;
  };
  isSuperadmin: boolean;
  syncingSourceId: string | null;
  onSourceFormChange: Dispatch<SetStateAction<SourceFormState>>;
  onOpenDirectoryBrowser: () => Promise<void>;
  onCloseDirectoryBrowser: () => void;
  onBrowseDirectories: (rootId: string | null, relativePath: string | null) => Promise<void>;
  onSelectAndBrowseDirectory: (rootId: string | null, relativePath: string) => Promise<void>;
  onUseCurrentDirectory: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onDelete: (sourceId: string) => Promise<void>;
  onSync: (sourceId: string) => Promise<void>;
};

export function KnowledgeBaseSourcesSection({
  sources,
  sourceForm,
  sourceDirectoryBrowser,
  isSuperadmin,
  syncingSourceId,
  onSourceFormChange,
  onOpenDirectoryBrowser,
  onCloseDirectoryBrowser,
  onBrowseDirectories,
  onSelectAndBrowseDirectory,
  onUseCurrentDirectory,
  onSubmit,
  onDelete,
  onSync,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const browserPayload = sourceDirectoryBrowser.payload;

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
              onChange={(event) => {
                const value = event.currentTarget.value;
                onSourceFormChange((current) => ({ ...current, displayName: value }));
              }}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.sourceRelativePath")}</span>
            <input
              className="field-input"
              value={sourceForm.relativePath}
              onChange={(event) => {
                const value = event.currentTarget.value;
                onSourceFormChange((current) => ({ ...current, relativePath: value }));
              }}
            />
            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={() => void onOpenDirectoryBrowser()}>
                {t("contextManagement.actions.browse")}
              </button>
            </div>
            <p className="status-text">{t("contextManagement.states.sourceRelativePathHelp")}</p>
          </label>
          {sourceDirectoryBrowser.open ? (
            <div className="panel card-stack">
              <div className="platform-card-header">
                <div className="card-stack">
                  <h4 className="section-title">{t("contextManagement.sourceBrowser.title")}</h4>
                  <p className="status-text">{t("contextManagement.sourceBrowser.description")}</p>
                </div>
                <button type="button" className="btn btn-secondary" onClick={onCloseDirectoryBrowser}>
                  {t("platformControl.actions.cancel")}
                </button>
              </div>
              <label className="card-stack">
                <span className="field-label">{t("contextManagement.sourceBrowser.root")}</span>
                <select
                  className="field-input"
                  value={browserPayload?.selected_root_id ?? ""}
                  onChange={(event) => void onBrowseDirectories(event.currentTarget.value, "")}
                >
                  {(browserPayload?.roots ?? []).map((root) => (
                    <option key={root.id} value={root.id}>
                      {root.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <p className="status-text">
                {t("contextManagement.sourceBrowser.currentPath", {
                  path: browserPayload?.current_relative_path || t("contextManagement.sourceBrowser.rootDirectory"),
                })}
              </p>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={sourceDirectoryBrowser.loading || browserPayload?.parent_relative_path == null}
                  onClick={() => void onBrowseDirectories(browserPayload?.selected_root_id ?? null, browserPayload?.parent_relative_path ?? null)}
                >
                  {t("contextManagement.sourceBrowser.up")}
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={sourceDirectoryBrowser.loading || !browserPayload?.current_relative_path}
                  onClick={onUseCurrentDirectory}
                >
                  {t("contextManagement.sourceBrowser.useCurrent")}
                </button>
              </div>
              {sourceDirectoryBrowser.loading ? <p className="status-text">{t("contextManagement.sourceBrowser.loading")}</p> : null}
              {!sourceDirectoryBrowser.loading && (browserPayload?.directories.length ?? 0) === 0 ? (
                <p className="status-text">{t("contextManagement.sourceBrowser.empty")}</p>
              ) : null}
              {!sourceDirectoryBrowser.loading ? (
                <div className="card-stack">
                  {(browserPayload?.directories ?? []).map((directory) => (
                    <button
                      key={directory.relative_path}
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => void onSelectAndBrowseDirectory(browserPayload?.selected_root_id ?? null, directory.relative_path)}
                    >
                      {directory.relative_path}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.includeGlobs")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={sourceForm.includeGlobs}
              onChange={(event) => {
                const value = event.currentTarget.value;
                onSourceFormChange((current) => ({ ...current, includeGlobs: value }));
              }}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.excludeGlobs")}</span>
            <textarea
              className="field-input quote-admin-textarea"
              value={sourceForm.excludeGlobs}
              onChange={(event) => {
                const value = event.currentTarget.value;
                onSourceFormChange((current) => ({ ...current, excludeGlobs: value }));
              }}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("contextManagement.fields.lifecycleState")}</span>
            <select
              className="field-input"
              value={sourceForm.lifecycleState}
              onChange={(event) => {
                const value = event.currentTarget.value;
                onSourceFormChange((current) => ({ ...current, lifecycleState: value }));
              }}
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
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  onCloseDirectoryBrowser();
                  onSourceFormChange(createEmptySourceForm());
                }}
              >
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
                onClick={() => {
                  onCloseDirectoryBrowser();
                  onSourceFormChange({
                    id: source.id,
                    displayName: source.display_name,
                    relativePath: source.relative_path,
                    includeGlobs: source.include_globs.join("\n"),
                    excludeGlobs: source.exclude_globs.join("\n"),
                    lifecycleState: source.lifecycle_state,
                  });
                }}
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
