import { type Dispatch, type SetStateAction, useCallback, useEffect, useMemo, useState } from "react";
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
  hasActiveSyncRuns: boolean;
  showErrorFeedback: ReturnType<typeof useActionFeedback>["showErrorFeedback"];
  showSuccessFeedback: ReturnType<typeof useActionFeedback>["showSuccessFeedback"];
};

const ACTIVE_SYNC_RUN_STATUSES = new Set(["queued", "running"]);
const SYNC_RUN_POLL_INTERVAL_MS = 2000;

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
  const normalizedOptions = useMemo(() => ({
    loadDocuments: options.loadDocuments ?? false,
    loadSources: options.loadSources ?? false,
    loadSyncRuns: options.loadSyncRuns ?? false,
  }), [options.loadDocuments, options.loadSources, options.loadSyncRuns]);
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

  const hasActiveSyncRuns = useMemo(
    () => syncRuns.some((run) => ACTIVE_SYNC_RUN_STATUSES.has(run.status)),
    [syncRuns],
  );

  const reload = useCallback(async (): Promise<void> => {
    if (!token || !knowledgeBaseId) {
      return;
    }

    const payload = await loadKnowledgeBaseWorkspaceData(knowledgeBaseId, token, normalizedOptions);
    setKnowledgeBase(payload.knowledgeBase);
    setDocuments(payload.documents);
    setSources(payload.sources);
    setSyncRuns(payload.syncRuns);
  }, [knowledgeBaseId, normalizedOptions, token]);

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

  useEffect(() => {
    if (!token || !knowledgeBaseId || !normalizedOptions.loadSyncRuns || !hasActiveSyncRuns) {
      return;
    }
    let cancelled = false;
    let timeoutId: number | undefined;

    const poll = async (): Promise<void> => {
      try {
        await reload();
      } catch {
        // Keep polling active sync runs; transient refresh errors surface on the next explicit load.
      } finally {
        if (!cancelled) {
          timeoutId = window.setTimeout(() => {
            void poll();
          }, SYNC_RUN_POLL_INTERVAL_MS);
        }
      }
    };

    timeoutId = window.setTimeout(() => {
      void poll();
    }, SYNC_RUN_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [hasActiveSyncRuns, knowledgeBaseId, normalizedOptions.loadSyncRuns, reload, token]);

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
    hasActiveSyncRuns,
    showErrorFeedback,
    showSuccessFeedback,
  };
}
