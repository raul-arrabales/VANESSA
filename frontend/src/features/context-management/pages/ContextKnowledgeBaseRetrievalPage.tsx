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
          retrievalHybridAlpha={detail.retrievalHybridAlpha}
          retrievalQueryPreprocessing={detail.retrievalQueryPreprocessing}
          retrievalResults={detail.retrievalResults}
          retrievalResultCount={detail.retrievalResultCount}
          retrievalDurationMs={detail.retrievalDurationMs}
          completedQueryId={detail.completedQueryId}
          isQuerying={detail.isQuerying}
          onQueryChange={detail.setRetrievalQuery}
          onTopKChange={detail.setRetrievalTopK}
          onSearchMethodChange={detail.setRetrievalSearchMethod}
          onHybridAlphaChange={detail.setRetrievalHybridAlpha}
          onQueryPreprocessingChange={detail.setRetrievalQueryPreprocessing}
          onSubmit={detail.handleTestRetrieval}
        />
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
