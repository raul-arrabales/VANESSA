import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { listKnowledgeBases, type KnowledgeBase } from "../../../api/context";
import { useAuth } from "../../../auth/AuthProvider";
import { useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";

type UseContextKnowledgeBaseListResult = {
  knowledgeBases: KnowledgeBase[];
  errorMessage: string;
  loading: boolean;
  isSuperadmin: boolean;
};

export function useContextKnowledgeBaseList(): UseContextKnowledgeBaseListResult {
  const { t } = useTranslation("common");
  const location = useLocation();
  const { token, user } = useAuth();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useRouteActionFeedback(location.state);

  useEffect(() => {
    if (!token) {
      return;
    }
    const load = async (): Promise<void> => {
      setLoading(true);
      setErrorMessage("");
      try {
        setKnowledgeBases(await listKnowledgeBases(token));
      } catch (requestError) {
        setErrorMessage(requestError instanceof Error ? requestError.message : t("contextManagement.feedback.loadFailed"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [t, token]);

  return {
    knowledgeBases,
    errorMessage,
    loading,
    isSuperadmin: user?.role === "superadmin",
  };
}
