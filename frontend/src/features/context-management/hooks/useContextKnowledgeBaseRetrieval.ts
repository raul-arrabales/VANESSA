import { type Dispatch, type FormEvent, type SetStateAction, useState } from "react";
import { useTranslation } from "react-i18next";
import { queryKnowledgeBase } from "../../../api/context";
import type { KnowledgeBaseQueryPreprocessing, KnowledgeBaseQueryResult, KnowledgeBaseSearchMethod } from "../../../api/context";
import { getCurrentTimeMs } from "../../../utils/timing";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export type KnowledgeBaseRetrievalFormState = {
  query: string;
  topK: string;
  searchMethod: KnowledgeBaseSearchMethod;
  hybridAlpha: string;
  queryPreprocessing: KnowledgeBaseQueryPreprocessing;
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
  const [retrievalRun, setRetrievalRun] = useState<KnowledgeBaseRetrievalRunState | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || isQuerying) {
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
    },
    retrievalRun,
    isQuerying,
    retrievalActions: {
      setQuery: setRetrievalQuery,
      setTopK: setRetrievalTopK,
      setSearchMethod: setRetrievalSearchMethod,
      setHybridAlpha: setRetrievalHybridAlpha,
      setQueryPreprocessing: setRetrievalQueryPreprocessing,
      submit,
    },
  };
}
