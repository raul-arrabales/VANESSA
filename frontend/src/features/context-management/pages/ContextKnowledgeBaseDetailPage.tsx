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
            isSuperadmin={detail.isSuperadmin}
            isResyncing={detail.isResyncing}
            onFormChange={detail.setForm}
            onSave={detail.handleSaveKnowledgeBase}
            onDelete={detail.handleDeleteKnowledgeBase}
            onResync={detail.handleResyncKnowledgeBase}
          />
        </section>
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
