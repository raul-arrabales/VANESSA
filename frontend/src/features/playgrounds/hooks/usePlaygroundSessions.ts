import { useEffect, useMemo, useState } from "react";
import {
  createPlaygroundSession,
  getPlaygroundSession,
  listPlaygroundSessions,
  updatePlaygroundSession,
} from "../../../api/playgrounds";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import type { PlaygroundWorkspaceConfig, PlaygroundWorkspaceOptions, PlaygroundSessionViewModel } from "../types";
import { mapPlaygroundSessionDetail, mapPlaygroundSessionSummary } from "../types";
import { createDraftSession, sortSessions, upsertSession } from "../utils";

type UsePlaygroundSessionsParams = {
  token: string;
  isAuthenticated: boolean;
  isOptionsLoading: boolean;
  hasLoadedOptions: boolean;
  config: PlaygroundWorkspaceConfig;
  options: PlaygroundWorkspaceOptions;
};

export function usePlaygroundSessions({
  token,
  isAuthenticated,
  isOptionsLoading,
  hasLoadedOptions,
  config,
  options,
}: UsePlaygroundSessionsParams) {
  const { showErrorFeedback } = useActionFeedback();
  const [savedSessions, setSavedSessions] = useState<PlaygroundSessionViewModel[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<PlaygroundSessionViewModel | null>(null);
  const [activeError, setActiveError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isActiveSessionLoading, setIsActiveSessionLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated && token) {
      return;
    }
    setSavedSessions([]);
    setActiveSessionId(null);
    setActiveSession(null);
    setActiveError("");
    setHistoryError("");
    setIsHistoryLoading(false);
    setIsActiveSessionLoading(false);
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      return;
    }

    let cancelled = false;
    const loadHistory = async (): Promise<void> => {
      setIsHistoryLoading(true);
      try {
        const listed = await listPlaygroundSessions(config.playgroundKind, token);
        if (cancelled) {
          return;
        }
        const mapped = listed.map(mapPlaygroundSessionSummary);
        setSavedSessions((existing) => {
          let merged = existing.filter((session) => session.persistence === "saved");
          mapped.forEach((session) => {
            merged = upsertSession(merged, session);
          });
          return sortSessions(merged);
        });
        setHistoryError("");
      } catch (requestError) {
        if (!cancelled) {
          setHistoryError(requestError instanceof Error ? requestError.message : config.feedback.sessionsError);
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    };

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [
    config.feedback.sessionsError,
    config.playgroundKind,
    isAuthenticated,
    token,
  ]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      return;
    }
    if (config.sessionBootstrap.mode !== "draft-first") {
      return;
    }
    if (isOptionsLoading || !hasLoadedOptions) {
      return;
    }
    if (activeSessionId || activeSession) {
      return;
    }

    const draftSession = createDraftSession(config, options);
    setActiveSessionId(draftSession.id);
    setActiveSession(draftSession);
    setActiveError("");
  }, [
    activeSession,
    activeSessionId,
    config,
    hasLoadedOptions,
    isAuthenticated,
    isOptionsLoading,
    options,
    token,
  ]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      return;
    }
    if (config.sessionBootstrap.mode !== "saved-first") {
      return;
    }
    if (isOptionsLoading || !hasLoadedOptions || isHistoryLoading) {
      return;
    }
    if (activeSessionId) {
      return;
    }

    let cancelled = false;
    const bootstrapSavedFirst = async (): Promise<void> => {
      if (savedSessions.length > 0) {
        setActiveSessionId(savedSessions[0]?.id ?? null);
        return;
      }

      setIsActiveSessionLoading(true);
      try {
        const created = await createPlaygroundSession(
          {
            playground_kind: config.playgroundKind,
            assistant_ref: options.defaultAssistantRef ?? undefined,
            model_selection: { model_id: options.models[0]?.id ?? null },
            knowledge_binding: {
              knowledge_base_id: config.selectors.knowledgeBase
                ? options.defaultKnowledgeBaseId
                : null,
            },
          },
          token,
        );
        if (cancelled) {
          return;
        }
        const createdViewModel = mapPlaygroundSessionDetail(created);
        setSavedSessions([createdViewModel]);
        setActiveSessionId(createdViewModel.id);
        setActiveSession(createdViewModel);
        setActiveError("");
      } catch (requestError) {
        if (!cancelled) {
          setActiveError(requestError instanceof Error ? requestError.message : config.feedback.createError);
        }
      } finally {
        if (!cancelled) {
          setIsActiveSessionLoading(false);
        }
      }
    };

    void bootstrapSavedFirst();
    return () => {
      cancelled = true;
    };
  }, [
    activeSessionId,
    config.feedback.createError,
    config.playgroundKind,
    config.selectors.knowledgeBase,
    config.sessionBootstrap.mode,
    hasLoadedOptions,
    isAuthenticated,
    isHistoryLoading,
    isOptionsLoading,
    options.defaultAssistantRef,
    options.defaultKnowledgeBaseId,
    options.models,
    savedSessions,
    token,
  ]);

  useEffect(() => {
    if (!token || !activeSessionId) {
      setIsActiveSessionLoading(false);
      return;
    }
    if (isOptionsLoading || !hasLoadedOptions) {
      return;
    }
    if (activeSession?.id === activeSessionId && activeSession.persistence !== "saved") {
      setIsActiveSessionLoading(false);
      return;
    }
    if (activeSession?.id === activeSessionId && activeSession.persistence === "saved") {
      setIsActiveSessionLoading(false);
      return;
    }

    const summary = savedSessions.find((session) => session.id === activeSessionId);
    if (!summary) {
      setIsActiveSessionLoading(false);
      setActiveSession(null);
      return;
    }

    let cancelled = false;
    const loadActiveSession = async (): Promise<void> => {
      setIsActiveSessionLoading(true);
      try {
        const session = await getPlaygroundSession(activeSessionId, config.playgroundKind, token);
        const loadedSession = mapPlaygroundSessionDetail(session);
        const needsKnowledgeBaseRepair = (
          config.playgroundKind === "knowledge"
          && config.selectors.knowledgeBase
          && !session.knowledge_binding.knowledge_base_id
          && Boolean(options.defaultKnowledgeBaseId)
        );
        if (needsKnowledgeBaseRepair) {
          try {
            const repaired = await updatePlaygroundSession(
              activeSessionId,
              {
                knowledge_binding: {
                  knowledge_base_id: options.defaultKnowledgeBaseId,
                },
              },
              token,
            );
            if (!cancelled) {
              const repairedSummary = mapPlaygroundSessionSummary(repaired);
              setSavedSessions((existing) => upsertSession(existing, repairedSummary));
              setActiveSession({
                ...loadedSession,
                ...repairedSummary,
                messages: loadedSession.messages,
              });
              setActiveError("");
            }
            return;
          } catch (requestError) {
            if (!cancelled) {
              setActiveSession(loadedSession);
              setActiveError(requestError instanceof Error ? requestError.message : config.feedback.updateKnowledgeBaseError);
              showErrorFeedback(requestError, config.feedback.updateKnowledgeBaseError);
            }
            return;
          }
        }
        if (!cancelled) {
          setActiveSession(loadedSession);
          setActiveError("");
        }
      } catch (requestError) {
        if (!cancelled) {
          setActiveError(requestError instanceof Error ? requestError.message : config.feedback.sessionError);
        }
      } finally {
        if (!cancelled) {
          setIsActiveSessionLoading(false);
        }
      }
    };

    void loadActiveSession();
    return () => {
      cancelled = true;
    };
  }, [
    activeSession,
    activeSessionId,
    config.feedback.sessionError,
    config.feedback.updateKnowledgeBaseError,
    config.playgroundKind,
    config.selectors.knowledgeBase,
    hasLoadedOptions,
    isOptionsLoading,
    options.defaultKnowledgeBaseId,
    savedSessions,
    showErrorFeedback,
    token,
  ]);

  const canCreateSession = useMemo(() => {
    if (!hasLoadedOptions || isOptionsLoading) {
      return false;
    }
    if (config.sessionBootstrap.mode === "draft-first") {
      return true;
    }
    return options.models.length > 0 && savedSessions.every((session) => session.messageCount > 0);
  }, [
    config.sessionBootstrap.mode,
    hasLoadedOptions,
    isOptionsLoading,
    options.models.length,
    savedSessions,
  ]);

  return {
    savedSessions,
    setSavedSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    setActiveSession,
    activeError,
    setActiveError,
    historyError,
    setHistoryError,
    isHistoryLoading,
    isActiveSessionLoading,
    canCreateSession,
  };
}
