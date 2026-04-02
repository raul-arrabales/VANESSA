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
import { sortSessions } from "../utils";

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
  const [sessions, setSessions] = useState<PlaygroundSessionViewModel[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<PlaygroundSessionViewModel | null>(null);
  const [error, setError] = useState("");
  const [isBootstrapping, setIsBootstrapping] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setSessions([]);
      setActiveSessionId(null);
      setActiveSession(null);
      setError("");
      setIsBootstrapping(false);
      return;
    }
    if (isOptionsLoading || !hasLoadedOptions) {
      return;
    }

    let cancelled = false;
    const bootstrap = async (): Promise<void> => {
      setIsBootstrapping(true);
      try {
        const listed = await listPlaygroundSessions(config.playgroundKind, token);
        if (cancelled) {
          return;
        }
        if (listed.length === 0 && options.models.length > 0) {
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
          setSessions([createdViewModel]);
          setActiveSessionId(createdViewModel.id);
          setActiveSession(createdViewModel);
          setError("");
          return;
        }

        const mapped = sortSessions(listed.map(mapPlaygroundSessionSummary));
        setSessions(mapped);
        setActiveSessionId((current) => (
          current && mapped.some((session) => session.id === current)
            ? current
            : mapped[0]?.id ?? null
        ));
        setError("");
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : config.feedback.sessionsError);
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    };

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [
    config.feedback.sessionsError,
    config.playgroundKind,
    config.selectors.knowledgeBase,
    hasLoadedOptions,
    isAuthenticated,
    isOptionsLoading,
    options.defaultAssistantRef,
    options.defaultKnowledgeBaseId,
    options.models,
    token,
  ]);

  useEffect(() => {
    if (!token || !activeSessionId) {
      setActiveSession(null);
      return;
    }

    if (activeSession?.id === activeSessionId) {
      return;
    }

    let cancelled = false;
    const load = async (): Promise<void> => {
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
              setSessions((existing) => sortSessions([
                {
                  ...repairedSummary,
                  messages: [],
                },
                ...existing.filter((item) => item.id !== repairedSummary.id),
              ]));
              setActiveSession({
                ...loadedSession,
                ...repairedSummary,
                messages: loadedSession.messages,
              });
              setError("");
            }
            return;
          } catch (requestError) {
            if (!cancelled) {
              setActiveSession(loadedSession);
              setError(requestError instanceof Error ? requestError.message : config.feedback.updateKnowledgeBaseError);
              showErrorFeedback(requestError, config.feedback.updateKnowledgeBaseError);
            }
            return;
          }
        }
        if (!cancelled) {
          setActiveSession(loadedSession);
          setError("");
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : config.feedback.sessionError);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [
    activeSession?.id,
    activeSessionId,
    config.feedback.sessionError,
    config.feedback.updateKnowledgeBaseError,
    config.playgroundKind,
    config.selectors.knowledgeBase,
    options.defaultKnowledgeBaseId,
    showErrorFeedback,
    token,
  ]);

  const canCreateSession = useMemo(
    () => options.models.length > 0 && sessions.every((session) => session.messageCount > 0),
    [options.models.length, sessions],
  );

  return {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    setActiveSession,
    error,
    setError,
    isBootstrapping,
    canCreateSession,
  };
}
