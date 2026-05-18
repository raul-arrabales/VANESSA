import type { CatalogMcpServerSpec } from "../../api/catalog";

export const MCP_METADATA_CATEGORY_OPTIONS: CatalogMcpServerSpec["metadata"]["category"][] = [
  "web_search",
  "knowledge_retrieval",
  "code_execution",
  "data_analysis",
  "automation",
  "communication",
  "custom",
];
