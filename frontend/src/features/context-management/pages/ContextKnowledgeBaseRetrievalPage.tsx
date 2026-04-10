import { ContextKnowledgeBaseWorkspaceFrame } from "../components/ContextKnowledgeBaseWorkspaceFrame";
import { KnowledgeBaseRetrievalSection } from "../components/KnowledgeBaseRetrievalSection";
import { useContextKnowledgeBaseRetrieval } from "../hooks/useContextKnowledgeBaseRetrieval";
import { schemaPropertiesFromSchema } from "../schemaEditor";

export default function ContextKnowledgeBaseRetrievalPage(): JSX.Element {
  const detail = useContextKnowledgeBaseRetrieval();

  return (
    <ContextKnowledgeBaseWorkspaceFrame knowledgeBase={detail.knowledgeBase} loading={detail.loading}>
      {() => (
        <KnowledgeBaseRetrievalSection
          schemaProperties={schemaPropertiesFromSchema(detail.knowledgeBase?.schema ?? {})}
          retrievalForm={detail.retrievalForm}
          retrievalRun={detail.retrievalRun}
          retrievalActions={detail.retrievalActions}
          isQuerying={detail.isQuerying}
        />
      )}
    </ContextKnowledgeBaseWorkspaceFrame>
  );
}
