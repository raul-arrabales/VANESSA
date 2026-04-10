import { type Dispatch, type FormEvent, type SetStateAction, useState } from "react";
import { useTranslation } from "react-i18next";
import { queryKnowledgeBase } from "../../../api/context";
import type { KnowledgeBaseQueryPreprocessing, KnowledgeBaseQueryResult, KnowledgeBaseSearchMethod } from "../../../api/context";
import { getCurrentTimeMs } from "../../../utils/timing";
import {
  buildMetadataRecord,
  MetadataEditorValidationError,
} from "../metadataEditor";
import type { MetadataEntryFormState } from "../types";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export type KnowledgeBaseRetrievalFormState = {
  query: string;
  topK: string;
  searchMethod: KnowledgeBaseSearchMethod;
  hybridAlpha: string;
  queryPreprocessing: KnowledgeBaseQueryPreprocessing;
  filters: MetadataEntryFormState[];
};

export type KnowledgeBaseRetrievalRunState = {
  results: KnowledgeBaseQueryResult[];
  resultCount: number;
  durationMs: number;
  completedQueryId: number;
};

export type KnowledgeBaseRetrievalActions = {
  setQuery: Dispatch<SetStateAction<string>>;
  setTopK: Dispatch<SetStateAction<string>>;
  setSearchMethod: Dispatch<SetStateAction<KnowledgeBaseSearchMethod>>;
  setHybridAlpha: Dispatch<SetStateAction<string>>;
  setQueryPreprocessing: Dispatch<SetStateAction<KnowledgeBaseQueryPreprocessing>>;
  setFilters: Dispatch<SetStateAction<MetadataEntryFormState[]>>;
  submit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export type ContextKnowledgeBaseRetrievalResult = ReturnType<typeof useContextKnowledgeBaseLoader> & {
  retrievalForm: KnowledgeBaseRetrievalFormState;
  retrievalRun: KnowledgeBaseRetrievalRunState | null;
  isQuerying: boolean;
  retrievalActions: KnowledgeBaseRetrievalActions;
};

export function useContextKnowledgeBaseRetrieval(): ContextKnowledgeBaseRetrievalResult {
  const { t } = useTranslation("common");
  const workspace = useContextKnowledgeBaseLoader();
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalTopK, setRetrievalTopK] = useState("5");
  const [retrievalSearchMethod, setRetrievalSearchMethod] = useState<KnowledgeBaseSearchMethod>("semantic");
  const [retrievalHybridAlpha, setRetrievalHybridAlpha] = useState("0.5");
  const [retrievalQueryPreprocessing, setRetrievalQueryPreprocessing] = useState<KnowledgeBaseQueryPreprocessing>("none");
  const [retrievalFilters, setRetrievalFilters] = useState<MetadataEntryFormState[]>([]);
  const [retrievalRun, setRetrievalRun] = useState<KnowledgeBaseRetrievalRunState | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || isQuerying) {
      return;
    }
    let filters: Record<string, unknown>;
    try {
      filters = buildMetadataRecord(retrievalFilters, workspace.knowledgeBase.schema);
    } catch (requestError) {
      if (requestError instanceof MetadataEditorValidationError) {
        workspace.showErrorFeedback(getMetadataValidationMessage(requestError, t), t("contextManagement.feedback.queryFailed"));
        return;
      }
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.queryFailed"));
      return;
    }
    const startedAt = getCurrentTimeMs();
    setIsQuerying(true);
    try {
      const parsedHybridAlpha = Number.parseFloat(retrievalHybridAlpha);
      const response = await queryKnowledgeBase(
        workspace.knowledgeBase.id,
        {
          query_text: retrievalQuery,
          top_k: Number.parseInt(retrievalTopK, 10) || 5,
          search_method: retrievalSearchMethod,
          query_preprocessing: retrievalQueryPreprocessing,
          ...(Object.keys(filters).length > 0 ? { filters } : {}),
          ...(retrievalSearchMethod === "hybrid"
            ? { hybrid_alpha: Number.isFinite(parsedHybridAlpha) ? parsedHybridAlpha : 0.5 }
            : {}),
        },
        workspace.token,
      );
      setRetrievalRun((current) => ({
        results: response.results,
        resultCount: response.retrieval.result_count,
        durationMs: Math.max(0, getCurrentTimeMs() - startedAt),
        completedQueryId: (current?.completedQueryId ?? 0) + 1,
      }));
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.queryFailed"));
    } finally {
      setIsQuerying(false);
    }
  }

  return {
    ...workspace,
    retrievalForm: {
      query: retrievalQuery,
      topK: retrievalTopK,
      searchMethod: retrievalSearchMethod,
      hybridAlpha: retrievalHybridAlpha,
      queryPreprocessing: retrievalQueryPreprocessing,
      filters: retrievalFilters,
    },
    retrievalRun,
    isQuerying,
    retrievalActions: {
      setQuery: setRetrievalQuery,
      setTopK: setRetrievalTopK,
      setSearchMethod: setRetrievalSearchMethod,
      setHybridAlpha: setRetrievalHybridAlpha,
      setQueryPreprocessing: setRetrievalQueryPreprocessing,
      setFilters: setRetrievalFilters,
      submit,
    },
  };
}

function getMetadataValidationMessage(
  error: MetadataEditorValidationError,
  t: ReturnType<typeof useTranslation<"common">>["t"],
): string {
  if (error.code === "duplicate_property") {
    return t("contextManagement.feedback.metadataDuplicateProperty");
  }
  if (error.code === "missing_property_name") {
    return t("contextManagement.feedback.metadataPropertyNameRequired");
  }
  if (error.code === "invalid_number") {
    return t("contextManagement.feedback.metadataInvalidNumber");
  }
  if (error.code === "invalid_int") {
    return t("contextManagement.feedback.metadataInvalidInteger");
  }
  if (error.code === "invalid_boolean") {
    return t("contextManagement.feedback.metadataInvalidBoolean");
  }
  return t("contextManagement.feedback.metadataInvalidText");
}
