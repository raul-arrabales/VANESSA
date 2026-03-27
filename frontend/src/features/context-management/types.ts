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

export const EMPTY_SOURCE_FORM: SourceFormState = {
  id: null,
  displayName: "",
  relativePath: "",
  includeGlobs: "",
  excludeGlobs: "",
  lifecycleState: "active",
};

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
