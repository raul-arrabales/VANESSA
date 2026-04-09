import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { KnowledgeSourceDirectoriesResponse } from "../../../api/context";
import { createEmptySourceForm, type SourceFormState } from "../types";

type Props = {
  sourceForm: SourceFormState;
  sourceDirectoryBrowser: {
    open: boolean;
    loading: boolean;
    payload: KnowledgeSourceDirectoriesResponse | null;
    usedPaths: Set<string>;
    currentPathUsed: boolean;
  };
  onSourceFormChange: Dispatch<SetStateAction<SourceFormState>>;
  onOpenDirectoryBrowser: () => Promise<void>;
  onCloseDirectoryBrowser: () => void;
  onBrowseDirectories: (rootId: string | null, relativePath: string | null) => Promise<void>;
  onSelectAndBrowseDirectory: (rootId: string | null, relativePath: string) => Promise<void>;
  onUseCurrentDirectory: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function KnowledgeBaseSourceEditorSection({
  sourceForm,
  sourceDirectoryBrowser,
  onSourceFormChange,
  onOpenDirectoryBrowser,
  onCloseDirectoryBrowser,
  onBrowseDirectories,
  onSelectAndBrowseDirectory,
  onUseCurrentDirectory,
  onSubmit,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const browserPayload = sourceDirectoryBrowser.payload;
  const isEditing = sourceForm.id !== null;

  return (
    <section className="panel card-stack">
      <div className="platform-card-header">
        <div className="card-stack">
          <h3 className="section-title">
            {isEditing ? t("contextManagement.sourceViews.editTitle") : t("contextManagement.sourceViews.addTitle")}
          </h3>
          <p className="status-text">
            {isEditing
              ? t("contextManagement.sourceViews.editDescription")
              : t("contextManagement.sourceViews.addDescription")}
          </p>
          <p className="status-text">{t("contextManagement.states.supportedFileTypes")}</p>
        </div>
      </div>

      <form className="card-stack" onSubmit={(event) => void onSubmit(event)}>
        <label className="card-stack" htmlFor="kb-source-display-name">
          <span className="field-label">{t("contextManagement.fields.sourceDisplayName")}</span>
          <input
            id="kb-source-display-name"
            className="field-input"
            value={sourceForm.displayName}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onSourceFormChange((current) => ({ ...current, displayName: value }));
            }}
          />
        </label>
        <div className="card-stack">
          <span className="field-label">{t("contextManagement.actions.browse")}</span>
          <p className="status-text">{t("contextManagement.states.sourcePathEntryHelp")}</p>
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={() => void onOpenDirectoryBrowser()}>
              {t("contextManagement.actions.browse")}
            </button>
          </div>
        </div>
        <label className="card-stack" htmlFor="kb-source-relative-path">
          <span className="field-label">{t("contextManagement.fields.sourceRelativePath")}</span>
          <input
            id="kb-source-relative-path"
            className="field-input"
            value={sourceForm.relativePath}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onSourceFormChange((current) => ({ ...current, relativePath: value }));
            }}
          />
          <p className="status-text">{t("contextManagement.states.sourceRelativePathHelp")}</p>
        </label>
        {sourceDirectoryBrowser.open ? (
          <div className="panel panel-nested card-stack">
            <div className="platform-card-header">
              <div className="card-stack">
                <h4 className="section-title">{t("contextManagement.sourceBrowser.title")}</h4>
                <p className="status-text">{t("contextManagement.sourceBrowser.description")}</p>
              </div>
              <button type="button" className="btn btn-secondary" onClick={onCloseDirectoryBrowser}>
                {t("platformControl.actions.cancel")}
              </button>
            </div>
            <label className="card-stack" htmlFor="kb-source-browser-root">
              <span className="field-label">{t("contextManagement.sourceBrowser.root")}</span>
              <select
                id="kb-source-browser-root"
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
                disabled={sourceDirectoryBrowser.loading || !browserPayload?.current_relative_path || sourceDirectoryBrowser.currentPathUsed}
                onClick={onUseCurrentDirectory}
              >
                {t("contextManagement.sourceBrowser.useCurrent")}
              </button>
            </div>
            {sourceDirectoryBrowser.currentPathUsed ? (
              <p className="status-text">{t("contextManagement.sourceBrowser.currentPathUsed")}</p>
            ) : null}
            {sourceDirectoryBrowser.loading ? <p className="status-text">{t("contextManagement.sourceBrowser.loading")}</p> : null}
            {!sourceDirectoryBrowser.loading && (browserPayload?.directories.length ?? 0) === 0 ? (
              <p className="status-text">{t("contextManagement.sourceBrowser.empty")}</p>
            ) : null}
            {!sourceDirectoryBrowser.loading ? (
              <div className="card-stack">
                {(browserPayload?.directories ?? []).map((directory) => {
                  const isUsed = sourceDirectoryBrowser.usedPaths.has(directory.relative_path.trim().replace(/^\/+|\/+$/g, ""));
                  return (
                    <button
                      key={directory.relative_path}
                      type="button"
                      className="btn btn-secondary"
                      disabled={isUsed}
                      onClick={() => void onSelectAndBrowseDirectory(browserPayload?.selected_root_id ?? null, directory.relative_path)}
                    >
                      {directory.relative_path}
                      {isUsed ? ` (${t("contextManagement.sourceBrowser.used")})` : ""}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : null}
        <label className="card-stack" htmlFor="kb-source-include-globs">
          <span className="field-label">{t("contextManagement.fields.includeGlobs")}</span>
          <textarea
            id="kb-source-include-globs"
            className="field-input quote-admin-textarea"
            value={sourceForm.includeGlobs}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onSourceFormChange((current) => ({ ...current, includeGlobs: value }));
            }}
          />
        </label>
        <label className="card-stack" htmlFor="kb-source-exclude-globs">
          <span className="field-label">{t("contextManagement.fields.excludeGlobs")}</span>
          <textarea
            id="kb-source-exclude-globs"
            className="field-input quote-admin-textarea"
            value={sourceForm.excludeGlobs}
            onChange={(event) => {
              const value = event.currentTarget.value;
              onSourceFormChange((current) => ({ ...current, excludeGlobs: value }));
            }}
          />
        </label>
        <label className="card-stack" htmlFor="kb-source-lifecycle-state">
          <span className="field-label">{t("contextManagement.fields.lifecycleState")}</span>
          <select
            id="kb-source-lifecycle-state"
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
    </section>
  );
}
