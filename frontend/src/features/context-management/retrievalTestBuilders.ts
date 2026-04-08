import type {
  KnowledgeBaseQueryPreprocessing,
  KnowledgeBaseQueryResponse,
  KnowledgeBaseQueryResult,
  KnowledgeBaseSearchMethod,
} from "../../api/context";

type QueryResultOverrides = Partial<KnowledgeBaseQueryResult> & {
  metadata?: Record<string, unknown>;
  relevance_components?: KnowledgeBaseQueryResult["relevance_components"];
};

export function buildKnowledgeBaseQueryResult(
  overrides: QueryResultOverrides = {},
): KnowledgeBaseQueryResult {
  return {
    id: overrides.id ?? "doc-1",
    title: overrides.title ?? "Architecture Overview",
    text: overrides.text ?? "Retrieved chunk previews show the first tokens.",
    uri: overrides.uri ?? null,
    source_type: overrides.source_type ?? "manual",
    metadata: overrides.metadata ?? {
      document_id: "doc-1",
      chunk_index: 0,
      source_name: "Docs folder",
    },
    chunk_length_tokens: overrides.chunk_length_tokens ?? 12,
    relevance_score: overrides.relevance_score ?? 0.742,
    relevance_kind: overrides.relevance_kind ?? "similarity",
    relevance_components: overrides.relevance_components,
  };
}

export function buildKnowledgeBaseQueryResponse(options?: {
  searchMethod?: KnowledgeBaseSearchMethod;
  queryPreprocessing?: KnowledgeBaseQueryPreprocessing;
  hybridAlpha?: number;
  results?: KnowledgeBaseQueryResult[];
  topK?: number;
}): KnowledgeBaseQueryResponse {
  const results = options?.results ?? [buildKnowledgeBaseQueryResult()];
  return {
    knowledge_base_id: "kb-primary",
    retrieval: {
      index: "kb_product_docs",
      result_count: results.length,
      top_k: options?.topK ?? 5,
      search_method: options?.searchMethod ?? "semantic",
      query_preprocessing: options?.queryPreprocessing ?? "none",
      ...(typeof options?.hybridAlpha === "number" ? { hybrid_alpha: options.hybridAlpha } : {}),
    },
    results,
  };
}
