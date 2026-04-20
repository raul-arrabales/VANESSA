import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseOverviewSection } from "../components/KnowledgeBaseOverviewSection";
import { useContextKnowledgeBaseOverview } from "../hooks/useContextKnowledgeBaseOverview";

export default function ContextKnowledgeBaseDetailPage(): JSX.Element {
  const detail = useContextKnowledgeBaseOverview();

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {(knowledgeBase) => (
        <section className="card-stack">
          <KnowledgeBaseOverviewSection
            knowledgeBase={knowledgeBase}
            form={detail.form}
            totalSourceCount={detail.sources.length}
            syncedSourceCount={detail.sources.filter((source) => source.last_sync_status === "ready").length}
            isDeleteDialogOpen={detail.isDeleteDialogOpen}
            isDeleting={detail.isDeleting}
            isSuperadmin={detail.isSuperadmin}
            isResyncing={detail.isResyncing}
            activeResyncRun={detail.activeResyncRun}
            onFormChange={detail.setForm}
            onCloseDeleteDialog={detail.closeDeleteDialog}
            onConfirmDelete={detail.confirmDeleteKnowledgeBase}
            onOpenDeleteDialog={detail.openDeleteDialog}
            onSave={detail.handleSaveKnowledgeBase}
            onResync={detail.handleResyncKnowledgeBase}
          />
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
