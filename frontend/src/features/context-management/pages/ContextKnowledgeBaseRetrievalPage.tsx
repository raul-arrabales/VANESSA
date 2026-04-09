import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseRetrievalSection } from "../components/KnowledgeBaseRetrievalSection";
import { useContextKnowledgeBaseRetrieval } from "../hooks/useContextKnowledgeBaseRetrieval";

export default function ContextKnowledgeBaseRetrievalPage(): JSX.Element {
  const detail = useContextKnowledgeBaseRetrieval();

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <KnowledgeBaseRetrievalSection
          retrievalForm={detail.retrievalForm}
          retrievalRun={detail.retrievalRun}
          retrievalActions={detail.retrievalActions}
          isQuerying={detail.isQuerying}
        />
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
