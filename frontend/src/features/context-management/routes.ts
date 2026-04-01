export type ContextKnowledgeBaseWorkspaceSection =
  | "overview"
  | "sources"
  | "retrieval"
  | "upload"
  | "documents";

export const CONTEXT_KNOWLEDGE_BASE_WORKSPACE_NAV_ITEMS: ReadonlyArray<{
  section: ContextKnowledgeBaseWorkspaceSection;
  labelKey: string;
}> = [
  { section: "overview", labelKey: "contextManagement.navigation.overview" },
  { section: "sources", labelKey: "contextManagement.navigation.sources" },
  { section: "retrieval", labelKey: "contextManagement.navigation.retrieval" },
  { section: "upload", labelKey: "contextManagement.navigation.upload" },
  { section: "documents", labelKey: "contextManagement.navigation.documents" },
];

export function buildKnowledgeBaseWorkspacePath(
  knowledgeBaseId: string,
  section: ContextKnowledgeBaseWorkspaceSection = "overview",
): string {
  const basePath = `/control/context/${encodeURIComponent(knowledgeBaseId)}`;
  return section === "overview" ? basePath : `${basePath}/${section}`;
}

export function buildKnowledgeBaseDocumentViewPath(knowledgeBaseId: string, documentId: string): string {
  return `${buildKnowledgeBaseWorkspacePath(knowledgeBaseId, "documents")}/${encodeURIComponent(documentId)}/view`;
}
