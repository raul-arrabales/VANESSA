import { type Dispatch, type FormEvent, type SetStateAction, useState } from "react";
import { useTranslation } from "react-i18next";
import { queryKnowledgeBase } from "../../../api/context";
import type { KnowledgeBaseQueryPreprocessing, KnowledgeBaseQueryResult, KnowledgeBaseSearchMethod } from "../../../api/context";
import { useContextKnowledgeBaseLoader } from "./useContextKnowledgeBaseLoader";

export type ContextKnowledgeBaseRetrievalResult = ReturnType<typeof useContextKnowledgeBaseLoader> & {
  retrievalQuery: string;
  retrievalTopK: string;
  retrievalSearchMethod: KnowledgeBaseSearchMethod;
  retrievalQueryPreprocessing: KnowledgeBaseQueryPreprocessing;
  retrievalResults: KnowledgeBaseQueryResult[];
  retrievalResultCount: number | null;
  isQuerying: boolean;
  setRetrievalQuery: Dispatch<SetStateAction<string>>;
  setRetrievalTopK: Dispatch<SetStateAction<string>>;
  setRetrievalSearchMethod: Dispatch<SetStateAction<KnowledgeBaseSearchMethod>>;
  setRetrievalQueryPreprocessing: Dispatch<SetStateAction<KnowledgeBaseQueryPreprocessing>>;
  handleTestRetrieval: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

export function useContextKnowledgeBaseRetrieval(): ContextKnowledgeBaseRetrievalResult {
  const { t } = useTranslation("common");
  const workspace = useContextKnowledgeBaseLoader();
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalTopK, setRetrievalTopK] = useState("5");
  const [retrievalSearchMethod, setRetrievalSearchMethod] = useState<KnowledgeBaseSearchMethod>("semantic");
  const [retrievalQueryPreprocessing, setRetrievalQueryPreprocessing] = useState<KnowledgeBaseQueryPreprocessing>("none");
  const [retrievalResults, setRetrievalResults] = useState<KnowledgeBaseQueryResult[]>([]);
  const [retrievalResultCount, setRetrievalResultCount] = useState<number | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);

  async function handleTestRetrieval(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!workspace.token || !workspace.knowledgeBase || isQuerying) {
      return;
    }
    setIsQuerying(true);
    try {
      const response = await queryKnowledgeBase(
        workspace.knowledgeBase.id,
        {
          query_text: retrievalQuery,
          top_k: Number.parseInt(retrievalTopK, 10) || 5,
          search_method: retrievalSearchMethod,
          query_preprocessing: retrievalQueryPreprocessing,
        },
        workspace.token,
      );
      setRetrievalResults(response.results);
      setRetrievalResultCount(response.retrieval.result_count);
    } catch (requestError) {
      workspace.showErrorFeedback(requestError, t("contextManagement.feedback.queryFailed"));
    } finally {
      setIsQuerying(false);
    }
  }

  return {
    ...workspace,
    retrievalQuery,
    retrievalTopK,
    retrievalSearchMethod,
    retrievalQueryPreprocessing,
    retrievalResults,
    retrievalResultCount,
    isQuerying,
    setRetrievalQuery,
    setRetrievalTopK,
    setRetrievalSearchMethod,
    setRetrievalQueryPreprocessing,
    handleTestRetrieval,
  };
}
