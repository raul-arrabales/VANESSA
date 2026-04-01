import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  getKnowledgeBase,
  listKnowledgeBaseDocuments,
  listKnowledgeSources,
  listKnowledgeSyncRuns,
} from "../../../api/context";
import type {
  KnowledgeBase,
  KnowledgeDocument,
  KnowledgeSource,
  KnowledgeSyncRun,
} from "../../../api/context";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback, useRouteActionFeedback } from "../../../feedback/ActionFeedbackProvider";

export type ContextKnowledgeBaseLoaderOptions = {
  loadDocuments?: boolean;
  loadSources?: boolean;
  loadSyncRuns?: boolean;
};

export type ContextKnowledgeBaseLoaderResult = {
  knowledgeBaseId: string;
  knowledgeBase: KnowledgeBase | null;
  loading: boolean;
  isSuperadmin: boolean;
  reload: () => Promise<void>;
  token: string;
  setKnowledgeBase: Dispatch<SetStateAction<KnowledgeBase | null>>;
  documents: KnowledgeDocument[];
  setDocuments: Dispatch<SetStateAction<KnowledgeDocument[]>>;
  sources: KnowledgeSource[];
  setSources: Dispatch<SetStateAction<KnowledgeSource[]>>;
  syncRuns: KnowledgeSyncRun[];
  setSyncRuns: Dispatch<SetStateAction<KnowledgeSyncRun[]>>;
  showErrorFeedback: ReturnType<typeof useActionFeedback>["showErrorFeedback"];
  showSuccessFeedback: ReturnType<typeof useActionFeedback>["showSuccessFeedback"];
};

type ContextKnowledgeBaseLoaderPayload = {
  knowledgeBase: KnowledgeBase;
  documents: KnowledgeDocument[];
  sources: KnowledgeSource[];
  syncRuns: KnowledgeSyncRun[];
};

async function loadKnowledgeBaseWorkspaceData(
  knowledgeBaseId: string,
  token: string,
  options: Required<ContextKnowledgeBaseLoaderOptions>,
): Promise<ContextKnowledgeBaseLoaderPayload> {
  const [knowledgeBase, documents, sources, syncRuns] = await Promise.all([
    getKnowledgeBase(knowledgeBaseId, token),
    options.loadDocuments ? listKnowledgeBaseDocuments(knowledgeBaseId, token) : Promise.resolve([]),
    options.loadSources ? listKnowledgeSources(knowledgeBaseId, token) : Promise.resolve([]),
    options.loadSyncRuns ? listKnowledgeSyncRuns(knowledgeBaseId, token) : Promise.resolve([]),
  ]);

  return { knowledgeBase, documents, sources, syncRuns };
}

export function useContextKnowledgeBaseLoader(
  options: ContextKnowledgeBaseLoaderOptions = {},
): ContextKnowledgeBaseLoaderResult {
  const normalizedOptions = {
    loadDocuments: options.loadDocuments ?? false,
    loadSources: options.loadSources ?? false,
    loadSyncRuns: options.loadSyncRuns ?? false,
  };
  const { t } = useTranslation("common");
  const { knowledgeBaseId = "" } = useParams();
  const location = useLocation();
  const { token, user } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [syncRuns, setSyncRuns] = useState<KnowledgeSyncRun[]>([]);
  const [loading, setLoading] = useState(true);
  const isSuperadmin = user?.role === "superadmin";

  useRouteActionFeedback(location.state);

  const reload = async (): Promise<void> => {
    if (!token || !knowledgeBaseId) {
      return;
    }

    const payload = await loadKnowledgeBaseWorkspaceData(knowledgeBaseId, token, normalizedOptions);
    setKnowledgeBase(payload.knowledgeBase);
    setDocuments(payload.documents);
    setSources(payload.sources);
    setSyncRuns(payload.syncRuns);
  };

  useEffect(() => {
    if (!token || !knowledgeBaseId) {
      return;
    }

    let isActive = true;
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const payload = await loadKnowledgeBaseWorkspaceData(knowledgeBaseId, token, normalizedOptions);
        if (!isActive) {
          return;
        }
        setKnowledgeBase(payload.knowledgeBase);
        setDocuments(payload.documents);
        setSources(payload.sources);
        setSyncRuns(payload.syncRuns);
      } catch (requestError) {
        if (isActive) {
          showErrorFeedback(requestError, t("contextManagement.feedback.loadFailed"));
        }
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      isActive = false;
    };
  }, [
    knowledgeBaseId,
    normalizedOptions.loadDocuments,
    normalizedOptions.loadSources,
    normalizedOptions.loadSyncRuns,
    showErrorFeedback,
    t,
    token,
  ]);

  return {
    knowledgeBaseId,
    knowledgeBase,
    loading,
    isSuperadmin,
    reload,
    token,
    setKnowledgeBase,
    documents,
    setDocuments,
    sources,
    setSources,
    syncRuns,
    setSyncRuns,
    showErrorFeedback,
    showSuccessFeedback,
  };
}
