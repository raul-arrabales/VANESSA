import type {
  KnowledgeBaseQueryResult,
  KnowledgeBaseSearchMethod,
} from "../../../api/context";
import type { PlaygroundKnowledgeReference, PlaygroundKnowledgeSource } from "../../../api/playgrounds";

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

const REFERENCE_URI_KEYS = ["uri", "file_uri", "source_uri", "url", "source_url"] as const;
const REFERENCE_PATH_KEYS = ["source_path", "source_filename", "file_path", "filename"] as const;

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

export function buildPlaygroundKnowledgeReferencesFromSources(
  sources: PlaygroundKnowledgeSource[],
): PlaygroundKnowledgeReference[] {
  const grouped = new Map<string, {
    title: string;
    description: string | null;
    uri: string | null;
    fileReference: string | null;
    pages: Set<number>;
    sourceIds: string[];
  }>();

  sources.forEach((source) => {
    const metadata = source.metadata ?? {};
    const groupKey = referenceGroupKey(source, metadata);
    if (!grouped.has(groupKey)) {
      grouped.set(groupKey, {
        title: referenceTitle(source, metadata),
        description: referenceDescription(source, metadata),
        uri: stringOrNull(source.uri) ?? firstMetadataString(metadata, REFERENCE_URI_KEYS),
        fileReference: referenceFileValue(source, metadata),
        pages: new Set<number>(),
        sourceIds: [],
      });
    }
    const group = grouped.get(groupKey);
    if (!group) {
      return;
    }
    group.sourceIds.push(source.id);
    metadataPageNumbers(metadata).forEach((page) => group.pages.add(page));
  });

  return [...grouped.values()].map((group, index) => ({
    id: `ref-${index + 1}`,
    citation_label: `[${index + 1}]`,
    title: group.title,
    description: group.description,
    uri: group.uri,
    file_reference: group.fileReference,
    pages: [...group.pages].sort((left, right) => left - right),
    source_ids: group.sourceIds,
  }));
}

function referenceGroupKey(source: PlaygroundKnowledgeSource, metadata: Record<string, unknown>): string {
  return (
    stringOrNull(source.uri)
    ?? firstMetadataString(metadata, REFERENCE_URI_KEYS)
    ?? firstMetadataString(metadata, REFERENCE_PATH_KEYS)
    ?? stringOrNull(metadata.document_id)
    ?? stringOrNull(metadata.title)
    ?? source.id
    ?? "unknown-source"
  );
}

function referenceTitle(source: PlaygroundKnowledgeSource, metadata: Record<string, unknown>): string {
  return (
    stringOrNull(source.title)
    ?? stringOrNull(metadata.title)
    ?? stringOrNull(metadata.source_display_name)
    ?? stringOrNull(metadata.source_name)
    ?? stringOrNull(metadata.source_filename)
    ?? stringOrNull(metadata.source_path)
    ?? source.id
    ?? "Source"
  );
}

function referenceDescription(source: PlaygroundKnowledgeSource, metadata: Record<string, unknown>): string | null {
  return (
    stringOrNull(metadata.description)
    ?? stringOrNull(metadata.source_description)
    ?? stringOrNull(metadata.source_display_name)
    ?? stringOrNull(metadata.source_name)
    ?? stringOrNull(source.source_type)
    ?? null
  );
}

function referenceFileValue(source: PlaygroundKnowledgeSource, metadata: Record<string, unknown>): string | null {
  return (
    firstMetadataString(metadata, REFERENCE_URI_KEYS)
    ?? firstMetadataString(metadata, REFERENCE_PATH_KEYS)
    ?? stringOrNull(source.uri)
    ?? stringOrNull(metadata.document_id)
    ?? source.id
    ?? null
  );
}

function firstMetadataString(
  metadata: Record<string, unknown>,
  keys: readonly string[],
): string | null {
  for (const key of keys) {
    const value = stringOrNull(metadata[key]);
    if (value) {
      return value;
    }
  }
  return null;
}

function metadataPageNumbers(metadata: Record<string, unknown>): Set<number> {
  const pages = new Set<number>();
  ["page", "page_number", "page_numbers", "pages"].forEach((key) => {
    coercePageNumbers(metadata[key]).forEach((page) => pages.add(page));
  });
  const start = firstPageNumber(metadata.page_start);
  const end = firstPageNumber(metadata.page_end);
  if (start !== null && end !== null) {
    const lower = Math.min(start, end);
    const upper = Math.max(start, end);
    if (upper - lower <= 50) {
      for (let page = lower; page <= upper; page += 1) {
        pages.add(page);
      }
    } else {
      pages.add(lower);
      pages.add(upper);
    }
  } else if (start !== null) {
    pages.add(start);
  } else if (end !== null) {
    pages.add(end);
  }
  return pages;
}

function coercePageNumbers(value: unknown): Set<number> {
  if (value === null || value === undefined || typeof value === "boolean") {
    return new Set();
  }
  if (typeof value === "number") {
    return Number.isInteger(value) && value > 0 ? new Set([value]) : new Set();
  }
  if (typeof value === "string") {
    const pages = new Set<number>();
    value.replace(/;/g, ",").split(",").forEach((part) => {
      const normalized = part.trim();
      if (!normalized) {
        return;
      }
      if (normalized.includes("-")) {
        const [startRaw, endRaw] = normalized.split("-", 2);
        const start = parsePositiveInt(startRaw);
        const end = parsePositiveInt(endRaw);
        if (start !== null && end !== null) {
          const lower = Math.min(start, end);
          const upper = Math.max(start, end);
          if (upper - lower <= 50) {
            for (let page = lower; page <= upper; page += 1) {
              pages.add(page);
            }
          } else {
            pages.add(lower);
            pages.add(upper);
          }
        }
        return;
      }
      const page = parsePositiveInt(normalized);
      if (page !== null) {
        pages.add(page);
      }
    });
    return pages;
  }
  if (Array.isArray(value)) {
    const pages = new Set<number>();
    value.forEach((item) => coercePageNumbers(item).forEach((page) => pages.add(page)));
    return pages;
  }
  return new Set();
}

function firstPageNumber(value: unknown): number | null {
  const pages = [...coercePageNumbers(value)];
  if (pages.length === 0) {
    return null;
  }
  return Math.min(...pages);
}

function stringOrNull(value: unknown): string | null {
  if (value === undefined || value === null) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized || null;
}

function parsePositiveInt(value: unknown): number | null {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  return parsed > 0 ? parsed : null;
}
