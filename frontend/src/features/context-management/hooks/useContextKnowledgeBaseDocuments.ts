import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export function useContextKnowledgeBaseDocuments() {
  return useContextKnowledgeBaseLoader({ loadDocuments: true });
}
