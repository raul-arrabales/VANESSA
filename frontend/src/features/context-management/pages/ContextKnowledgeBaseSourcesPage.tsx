import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import type { KnowledgeSource } from "../../../api/context";
import { KnowledgeBaseSourceEditorSection } from "../components/KnowledgeBaseSourceEditorSection";
import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseSourcesListSection } from "../components/KnowledgeBaseSourcesListSection";
import { KnowledgeBaseSyncHistorySection } from "../components/KnowledgeBaseSyncHistorySection";
import { useContextKnowledgeBaseSources } from "../hooks/useContextKnowledgeBaseSources";

type SourcesPageView = "add" | "list" | "history";

const SOURCES_PAGE_VIEW_ORDER: ReadonlyArray<SourcesPageView> = ["add", "list", "history"];

function resolveSourcesPageView(value: string | null, isSuperadmin: boolean): SourcesPageView {
  const defaultView: SourcesPageView = isSuperadmin ? "add" : "list";
  if (value === "add" && isSuperadmin) {
    return value;
  }
  if (value === "list" || value === "history") {
    return value;
  }
  return defaultView;
}

export default function ContextKnowledgeBaseSourcesPage(): JSX.Element {
  const { t } = useTranslation("common");
  const detail = useContextKnowledgeBaseSources();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = resolveSourcesPageView(searchParams.get("view"), detail.isSuperadmin);
  const availableViews = SOURCES_PAGE_VIEW_ORDER.filter((view) => detail.isSuperadmin || view !== "add");
  const submenuItems = availableViews.map((view) => ({
    id: view,
    label: t(`contextManagement.sourceViews.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

  function handleChangeView(view: SourcesPageView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  function handleEditSource(source: KnowledgeSource): void {
    detail.handleCloseSourceDirectoryBrowser();
    detail.setSourceForm({
      id: source.id,
      displayName: source.display_name,
      relativePath: source.relative_path,
      includeGlobs: source.include_globs.join("\n"),
      excludeGlobs: source.exclude_globs.join("\n"),
      lifecycleState: source.lifecycle_state,
    });
    handleChangeView("add");
  }

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <section className="card-stack">
          <section className="panel card-stack">
            <div className="card-stack">
              <h3 className="section-title">{t("contextManagement.sourcesTitle")}</h3>
              <p className="status-text">{t("contextManagement.sourcesDescription")}</p>
            </div>
            <PageSubmenuBar items={submenuItems} ariaLabel={t("contextManagement.sourceViews.aria")} />
          </section>
          {activeView === "add" ? (
            <KnowledgeBaseSourceEditorSection
              sourceForm={detail.sourceForm}
              sourceDirectoryBrowser={detail.sourceDirectoryBrowser}
              onSourceFormChange={detail.setSourceForm}
              onOpenDirectoryBrowser={detail.handleOpenSourceDirectoryBrowser}
              onCloseDirectoryBrowser={detail.handleCloseSourceDirectoryBrowser}
              onBrowseDirectories={detail.handleBrowseSourceDirectories}
              onSelectAndBrowseDirectory={detail.handleSelectAndBrowseSourceDirectory}
              onUseCurrentDirectory={detail.handleUseCurrentSourceDirectory}
              onSubmit={detail.handleSubmitSource}
            />
          ) : null}
          {activeView === "list" ? (
            <KnowledgeBaseSourcesListSection
              sources={detail.sources}
              isSuperadmin={detail.isSuperadmin}
              syncingSourceId={detail.syncingSourceId}
              onEdit={handleEditSource}
              onDelete={detail.handleDeleteSource}
              onSync={detail.handleSyncSource}
            />
          ) : null}
          {activeView === "history" ? <KnowledgeBaseSyncHistorySection syncRuns={detail.syncRuns} /> : null}
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
