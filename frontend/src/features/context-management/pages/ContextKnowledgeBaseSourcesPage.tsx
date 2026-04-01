import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseSourcesSection } from "../components/KnowledgeBaseSourcesSection";
import { KnowledgeBaseSyncHistorySection } from "../components/KnowledgeBaseSyncHistorySection";
import { useContextKnowledgeBaseSources } from "../hooks/useContextKnowledgeBaseSources";

export default function ContextKnowledgeBaseSourcesPage(): JSX.Element {
  const detail = useContextKnowledgeBaseSources();

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <section className="card-stack">
          <KnowledgeBaseSourcesSection
            sources={detail.sources}
            sourceForm={detail.sourceForm}
            sourceDirectoryBrowser={detail.sourceDirectoryBrowser}
            isSuperadmin={detail.isSuperadmin}
            syncingSourceId={detail.syncingSourceId}
            onSourceFormChange={detail.setSourceForm}
            onOpenDirectoryBrowser={detail.handleOpenSourceDirectoryBrowser}
            onCloseDirectoryBrowser={detail.handleCloseSourceDirectoryBrowser}
            onBrowseDirectories={detail.handleBrowseSourceDirectories}
            onSelectAndBrowseDirectory={detail.handleSelectAndBrowseSourceDirectory}
            onUseCurrentDirectory={detail.handleUseCurrentSourceDirectory}
            onSubmit={detail.handleSubmitSource}
            onDelete={detail.handleDeleteSource}
            onSync={detail.handleSyncSource}
          />
          <KnowledgeBaseSyncHistorySection syncRuns={detail.syncRuns} />
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
