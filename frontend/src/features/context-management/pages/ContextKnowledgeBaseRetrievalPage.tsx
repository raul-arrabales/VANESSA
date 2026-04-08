import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseRetrievalSection } from "../components/KnowledgeBaseRetrievalSection";
import { useContextKnowledgeBaseRetrieval } from "../hooks/useContextKnowledgeBaseRetrieval";

export default function ContextKnowledgeBaseRetrievalPage(): JSX.Element {
  const detail = useContextKnowledgeBaseRetrieval();

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <KnowledgeBaseRetrievalSection
          retrievalQuery={detail.retrievalQuery}
          retrievalTopK={detail.retrievalTopK}
          retrievalSearchMethod={detail.retrievalSearchMethod}
          retrievalQueryPreprocessing={detail.retrievalQueryPreprocessing}
          retrievalResults={detail.retrievalResults}
          retrievalResultCount={detail.retrievalResultCount}
          isQuerying={detail.isQuerying}
          onQueryChange={detail.setRetrievalQuery}
          onTopKChange={detail.setRetrievalTopK}
          onSearchMethodChange={detail.setRetrievalSearchMethod}
          onQueryPreprocessingChange={detail.setRetrievalQueryPreprocessing}
          onSubmit={detail.handleTestRetrieval}
        />
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
