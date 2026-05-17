import type { CatalogToolExecutionBackend } from "../../api/catalog";

export function catalogToolBackendLabelKey(executionBackend: CatalogToolExecutionBackend | string | undefined): string {
  if (executionBackend === "sandbox_python") {
    return "sandboxPython";
  }
  if (executionBackend === "mcp_gateway_web_search") {
    return "webSearch";
  }
  if (executionBackend === "knowledge_base_retrieval") {
    return "knowledgeBaseRetrieval";
  }
  return "internalHttp";
}
