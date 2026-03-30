import type {
  KnowledgeBase,
  KnowledgeBaseQueryResult,
  KnowledgeDocument,
  KnowledgeSource,
  KnowledgeSyncRun,
} from "../../api/context";

export type DocumentFormState = {
  id: string | null;
  title: string;
  sourceName: string;
  uri: string;
  text: string;
};

export type SourceFormState = {
  id: string | null;
  displayName: string;
  relativePath: string;
  includeGlobs: string;
  excludeGlobs: string;
  lifecycleState: string;
};

export const EMPTY_DOCUMENT_FORM: DocumentFormState = {
  id: null,
  title: "",
  sourceName: "",
  uri: "",
  text: "",
};

export const DEFAULT_SOURCE_INCLUDE_GLOBS = "*.md\n*.txt\n*.pdf\n*.json\n*.jsonl\n**/*.md\n**/*.txt\n**/*.pdf\n**/*.json\n**/*.jsonl";
export const DEFAULT_SOURCE_EXCLUDE_GLOBS = "**/.git/**\n**/node_modules/**\n**/venv/**\n**/*.log";

export function createEmptySourceForm(): SourceFormState {
  return {
    id: null,
    displayName: "",
    relativePath: "",
    includeGlobs: DEFAULT_SOURCE_INCLUDE_GLOBS,
    excludeGlobs: DEFAULT_SOURCE_EXCLUDE_GLOBS,
    lifecycleState: "active",
  };
}

export const EMPTY_SOURCE_FORM: SourceFormState = createEmptySourceForm();

export function parseGlobText(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export type ContextKnowledgeBaseDetailState = {
  knowledgeBase: KnowledgeBase | null;
  documents: KnowledgeDocument[];
  sources: KnowledgeSource[];
  syncRuns: KnowledgeSyncRun[];
  loading: boolean;
  isSuperadmin: boolean;
  form: {
    slug: string;
    displayName: string;
    description: string;
    lifecycleState: string;
  };
  documentForm: DocumentFormState;
  sourceForm: SourceFormState;
  uploadFiles: File[];
  retrievalQuery: string;
  retrievalTopK: string;
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
  isResyncing: boolean;
  isQuerying: boolean;
  syncingSourceId: string | null;
};
