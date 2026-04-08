import type {
  KnowledgeBaseQueryResult,
  KnowledgeBaseSearchMethod,
} from "../../../api/context";
import type { PlaygroundKnowledgeSource } from "../../../api/playgrounds";

export type RetrievalMetadataEntry = {
  key: string;
  value: string;
};

export type RetrievalComponentScoreKind = "semantic_score" | "keyword_score";

export type RetrievalComponentScoreRow = {
  kind: RetrievalComponentScoreKind;
  value: number;
};

export type RetrievalScoreKind = "similarity" | "keyword_score" | "hybrid_score";

export type RetrievalDisplaySource = {
  id: string;
  title?: string | null;
  text?: string | null;
  snippet?: string | null;
  metadata?: Record<string, unknown>;
  relevance_score?: number | null;
  relevance_kind?: string | null;
  relevance_components?: {
    semantic_score?: number;
    keyword_score?: number;
  } | null;
  score?: number | null;
  score_kind?: string | null;
};

export type RetrievalDisplayItem<TSource extends RetrievalDisplaySource = RetrievalDisplaySource> = {
  id: string;
  raw: TSource;
  displayTitle: string;
  displaySnippet: string;
  displayScoreKind: RetrievalScoreKind;
  displayScoreValue: number | null;
  displayMetadataEntries: RetrievalMetadataEntry[];
  displayOrdinal: number | null;
  displayComponentScoreRows: RetrievalComponentScoreRow[];
  isExpandable: boolean;
};

export function shouldShowHybridAlphaControl(searchMethod: KnowledgeBaseSearchMethod): boolean {
  return searchMethod === "hybrid";
}

export function sortRetrievalResultsByRelevance<T extends { relevance_score: number }>(results: T[]): T[] {
  return [...results].sort((left, right) => right.relevance_score - left.relevance_score);
}

export function getRetrievalScoreKind(
  result: Pick<RetrievalDisplaySource, "relevance_kind" | "score_kind">,
): RetrievalScoreKind {
  if (result.relevance_kind === "hybrid_score" || result.score_kind === "hybrid_score") {
    return "hybrid_score";
  }
  if (
    result.relevance_kind === "keyword_score"
    || result.score_kind === "keyword_score"
    || result.score_kind === "bm25"
    || result.score_kind === "text_match"
  ) {
    return "keyword_score";
  }
  return "similarity";
}

export function buildRetrievalPreview(text: string, previewTokenCount = 24): string {
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  if (tokens.length <= previewTokenCount) {
    return tokens.join(" ");
  }
  return `${tokens.slice(0, previewTokenCount).join(" ")}…`;
}

export function formatRetrievalMetadataValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") {
    return String(value);
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return JSON.stringify(value);
}

export function getVisibleRetrievalMetadataEntries(
  metadata: Record<string, unknown>,
): RetrievalMetadataEntry[] {
  return Object.entries(metadata)
    .filter(([, value]) => value !== null && value !== undefined && !(typeof value === "string" && value.trim() === ""))
    .map(([key, value]) => ({ key, value: formatRetrievalMetadataValue(value) }))
    .filter(({ value }) => value !== undefined && value !== "undefined");
}

export function getRetrievalComponentScoreRows(
  result: Pick<RetrievalDisplaySource, "relevance_kind" | "relevance_components">,
): RetrievalComponentScoreRow[] {
  if (result.relevance_kind !== "hybrid_score") {
    return [];
  }
  const rows: RetrievalComponentScoreRow[] = [];
  if (typeof result.relevance_components?.semantic_score === "number") {
    rows.push({
      kind: "semantic_score",
      value: result.relevance_components.semantic_score,
    });
  }
  if (typeof result.relevance_components?.keyword_score === "number") {
    rows.push({
      kind: "keyword_score",
      value: result.relevance_components.keyword_score,
    });
  }
  return rows;
}

export function buildOrdinalTitle(prefix: string, ordinal: number, title: string): string {
  return `${prefix} ${ordinal}: ${title}`;
}

export function mapRetrievalSourceToDisplayItem<TSource extends RetrievalDisplaySource>(
  source: TSource,
  options?: {
    ordinal?: number;
    ordinalPrefix?: string;
    previewTokenCount?: number;
  },
): RetrievalDisplayItem<TSource> {
  const title = String(source.title || source.id || "Source").trim() || "Source";
  const displayOrdinal = typeof options?.ordinal === "number" ? options.ordinal : null;
  const displayTitle = displayOrdinal !== null
    ? buildOrdinalTitle(options?.ordinalPrefix ?? "Chunk", displayOrdinal, title)
    : title;
  const text = typeof source.text === "string" ? source.text : "";
  const snippetSource = typeof source.snippet === "string" && source.snippet.trim()
    ? source.snippet
    : buildRetrievalPreview(text, options?.previewTokenCount);
  const metadata = source.metadata ?? {};
  const displayScoreValue = typeof source.relevance_score === "number"
    ? source.relevance_score
    : (typeof source.score === "number" ? source.score : null);

  return {
    id: source.id,
    raw: source,
    displayTitle,
    displaySnippet: snippetSource,
    displayScoreKind: getRetrievalScoreKind(source),
    displayScoreValue,
    displayMetadataEntries: getVisibleRetrievalMetadataEntries(metadata),
    displayOrdinal,
    displayComponentScoreRows: getRetrievalComponentScoreRows(source),
    isExpandable: text.trim().length > 0,
  };
}

export function mapKnowledgeBaseQueryResultToDisplayItem(
  result: KnowledgeBaseQueryResult,
  index: number,
): RetrievalDisplayItem<KnowledgeBaseQueryResult> {
  return mapRetrievalSourceToDisplayItem(result, {
    ordinal: index + 1,
    ordinalPrefix: "Chunk",
    previewTokenCount: 24,
  });
}

export function mapPlaygroundKnowledgeSourceToDisplayItem(
  source: PlaygroundKnowledgeSource,
): RetrievalDisplayItem<PlaygroundKnowledgeSource> {
  return mapRetrievalSourceToDisplayItem(source, {
    previewTokenCount: 24,
  });
}
