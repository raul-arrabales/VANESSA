import type { Dispatch, SetStateAction } from "react";
import { useRef } from "react";
import {
  createPlaygroundSession,
  deletePlaygroundSession,
  streamPlaygroundMessage,
  streamTemporaryPlaygroundMessage,
  updatePlaygroundSession,
} from "../../../api/playgrounds";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { hasSelector } from "../selectorConfig";
import type {
  PlaygroundMessageViewModel,
  PlaygroundRunStatus,
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
} from "../types";
import { mapPlaygroundSessionDetail, mapPlaygroundSessionSummary } from "../types";
import {
  createDraftSession,
  createTemporarySession,
  createOptimisticMessages,
  createTransientMessageId,
  removeSession,
  sortSessions,
  updateTransientAssistantMessage,
  updateTransientAssistantStatus,
  upsertSession,
} from "../utils";

type UsePlaygroundSessionActionsParams = {
  token: string;
  config: PlaygroundWorkspaceConfig;
  options: PlaygroundWorkspaceOptions;
  draft: string;
  setDraft: (value: string) => void;
  savedSessions: PlaygroundSessionViewModel[];
  setSavedSessions: Dispatch<SetStateAction<PlaygroundSessionViewModel[]>>;
  activeSession: PlaygroundSessionViewModel | null;
  setActiveSession: Dispatch<SetStateAction<PlaygroundSessionViewModel | null>>;
  setActiveSessionId: Dispatch<SetStateAction<string | null>>;
  setError: (value: string) => void;
  setIsSending: (value: boolean) => void;
  setIsSessionBusy: (value: boolean) => void;
  pinToBottomOnNextUpdate: (behavior?: ScrollBehavior) => void;
};

function buildTemporaryMessagePayload(
  session: PlaygroundSessionViewModel,
  prompt: string,
) {
  return {
    session_id: session.id,
    playground_kind: session.playgroundKind,
    title: session.title,
    assistant_ref: session.selectorState.assistantRef,
    model_selection: { model_id: session.selectorState.modelId },
    knowledge_binding: { knowledge_base_id: session.selectorState.knowledgeBaseId },
    messages: session.messages
      .filter((message) => message.role === "user" || message.role === "assistant")
      .map((message) => ({
        role: message.role,
        content: message.content,
      })),
    prompt,
  };
}

export function usePlaygroundSessionActions({
  token,
  config,
  options,
  draft,
  setDraft,
  savedSessions,
  setSavedSessions,
  activeSession,
  setActiveSession,
  setActiveSessionId,
  setError,
  setIsSending,
  setIsSessionBusy,
  pinToBottomOnNextUpdate,
}: UsePlaygroundSessionActionsParams) {
  const { showErrorFeedback } = useActionFeedback();
  const streamAbortRef = useRef<AbortController | null>(null);
  const hasKnowledgeBaseSelector = hasSelector(config, "knowledgeBase");

  const createOrResetDraftSession = (): PlaygroundSessionViewModel => {
    const nextDraft = createDraftSession(config, options, activeSession);
    setActiveSessionId(nextDraft.id);
    setActiveSession(nextDraft);
    setDraft("");
    setError("");
    return nextDraft;
  };

  const createTemporaryChat = (): PlaygroundSessionViewModel => {
    const nextTemporary = createTemporarySession(config, options, activeSession);
    setActiveSessionId(nextTemporary.id);
    setActiveSession(nextTemporary);
    setDraft("");
    setError("");
    return nextTemporary;
  };

  const createSession = async (): Promise<void> => {
    if (!token) {
      return;
    }

    if (config.sessionBootstrap.mode === "draft-first") {
      createOrResetDraftSession();
      return;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      const created = await createPlaygroundSession(
        {
          playground_kind: config.playgroundKind,
          assistant_ref: activeSession?.selectorState.assistantRef ?? options.defaultAssistantRef ?? undefined,
          model_selection: {
            model_id: activeSession?.selectorState.modelId ?? options.models[0]?.id ?? null,
          },
          knowledge_binding: {
            knowledge_base_id: hasKnowledgeBaseSelector
              ? (activeSession?.selectorState.knowledgeBaseId ?? options.defaultKnowledgeBaseId ?? options.knowledgeBases[0]?.id ?? null)
              : null,
          },
        },
        token,
      );
      const nextSession = mapPlaygroundSessionDetail(created);
      setSavedSessions((existing) => upsertSession(existing, nextSession));
      setActiveSessionId(nextSession.id);
      setActiveSession(nextSession);
      setDraft("");
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.createError);
    } finally {
      setIsSessionBusy(false);
    }
  };

  const updateSelectorState = async (
    sessionId: string,
    payload: {
      assistant_ref?: string;
      model_selection?: { model_id?: string | null };
      knowledge_binding?: { knowledge_base_id?: string | null };
    },
    fallbackMessage: string,
  ): Promise<void> => {
    if (!token || !activeSession) {
      return;
    }

    if (activeSession.id === sessionId && activeSession.persistence !== "saved") {
      setError("");
      setActiveSession((current) => (
        current && current.id === sessionId
          ? {
            ...current,
            selectorState: {
              assistantRef: payload.assistant_ref ?? current.selectorState.assistantRef,
              modelId: payload.model_selection?.model_id ?? current.selectorState.modelId,
              knowledgeBaseId: payload.knowledge_binding?.knowledge_base_id ?? current.selectorState.knowledgeBaseId,
            },
          }
          : current
      ));
      return;
    }

    setError("");
    try {
      const updated = await updatePlaygroundSession(sessionId, payload, token);
      const updatedViewModel = mapPlaygroundSessionSummary(updated);
      setSavedSessions((existing) => upsertSession(existing, updatedViewModel));
      setActiveSession((current) => (
        current && current.id === sessionId
          ? {
            ...current,
            ...updatedViewModel,
            messages: current.messages,
          }
          : current
      ));
    } catch (requestError) {
      showErrorFeedback(requestError, fallbackMessage);
    }
  };

  const renameSession = async (sessionId: string, nextTitle: string): Promise<boolean> => {
    if (!token) {
      return false;
    }

    const targetSession = savedSessions.find((session) => session.id === sessionId);
    if (!targetSession || targetSession.persistence === "draft") {
      return false;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      const updated = await updatePlaygroundSession(sessionId, { title: nextTitle }, token);
      const updatedViewModel = mapPlaygroundSessionSummary(updated);
      setSavedSessions((existing) => upsertSession(existing, updatedViewModel));
      setActiveSession((current) => (
        current && current.id === updatedViewModel.id && current.persistence === "saved"
          ? { ...current, ...updatedViewModel, messages: current.messages }
          : current
      ));
      return true;
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.renameError);
      return false;
    } finally {
      setIsSessionBusy(false);
    }
  };

  const deleteSession = async (sessionId: string): Promise<boolean> => {
    if (!token) {
      return false;
    }

    const targetSession = savedSessions.find((session) => session.id === sessionId);
    if (!targetSession || targetSession.persistence === "draft") {
      return false;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      await deletePlaygroundSession(sessionId, token);
      const remaining = removeSession(savedSessions, sessionId);
      const isDeletingActiveSavedSession = activeSession?.id === sessionId && activeSession.persistence === "saved";

      if (!isDeletingActiveSavedSession) {
        setSavedSessions(sortSessions(remaining));
        return true;
      }

      if (remaining.length === 0) {
        setSavedSessions([]);
        if (config.sessionBootstrap.mode === "draft-first") {
          createOrResetDraftSession();
        } else {
          const created = await createPlaygroundSession(
            {
              playground_kind: config.playgroundKind,
              assistant_ref: options.defaultAssistantRef ?? undefined,
              model_selection: { model_id: options.models[0]?.id ?? null },
              knowledge_binding: {
                knowledge_base_id: hasKnowledgeBaseSelector
                  ? options.defaultKnowledgeBaseId
                  : null,
              },
            },
            token,
          );
          const nextSession = mapPlaygroundSessionDetail(created);
          setSavedSessions([nextSession]);
          setActiveSessionId(nextSession.id);
          setActiveSession(nextSession);
        }
      } else {
        const sorted = sortSessions(remaining);
        setSavedSessions(sorted);
        setActiveSessionId(sorted[0]?.id ?? null);
        setActiveSession(null);
      }
      return true;
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.deleteError);
      return false;
    } finally {
      setIsSessionBusy(false);
    }
  };

  const persistDraftForSend = async (
    currentDraft: PlaygroundSessionViewModel,
  ): Promise<PlaygroundSessionViewModel | null> => {
    try {
      const created = await createPlaygroundSession(
        {
          playground_kind: config.playgroundKind,
          assistant_ref: currentDraft.selectorState.assistantRef ?? options.defaultAssistantRef ?? undefined,
          model_selection: { model_id: currentDraft.selectorState.modelId },
          knowledge_binding: {
            knowledge_base_id: hasKnowledgeBaseSelector
              ? currentDraft.selectorState.knowledgeBaseId
              : null,
          },
        },
        token,
      );
      const persistedSession = mapPlaygroundSessionDetail(created);
      setSavedSessions((existing) => upsertSession(existing, persistedSession));
      setActiveSessionId(persistedSession.id);
      setActiveSession(persistedSession);
      return persistedSession;
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.createError);
      return null;
    }
  };

  const restoreDraftAfterFailedFirstSend = async (
    draftSnapshot: PlaygroundSessionViewModel,
    createdSession: PlaygroundSessionViewModel | null,
    prompt: string,
  ): Promise<void> => {
    if (createdSession) {
      try {
        await deletePlaygroundSession(createdSession.id, token);
      } catch {
        // Best-effort cleanup; the local draft is still restored for the user.
      }
      setSavedSessions((existing) => removeSession(existing, createdSession.id));
    }
    setActiveSessionId(draftSnapshot.id);
    setActiveSession(draftSnapshot);
    setDraft(prompt);
  };

  const sendPrompt = async (): Promise<void> => {
    if (!token || !activeSession || !draft.trim()) {
      return;
    }
    if (!activeSession.selectorState.modelId) {
      setError(config.feedback.missingModel);
      return;
    }
    if (hasKnowledgeBaseSelector && !activeSession.selectorState.knowledgeBaseId) {
      setError(config.feedback.missingKnowledgeBase);
      return;
    }

    const prompt = draft.trim();
    const isDraftSession = activeSession.persistence === "draft";
    const isTemporarySession = activeSession.persistence === "temporary";
    const draftSnapshot = isDraftSession ? { ...activeSession, messages: [...activeSession.messages] } : null;
    let targetSession = activeSession;
    let createdFromDraft: PlaygroundSessionViewModel | null = null;

    if (isDraftSession) {
      const persisted = await persistDraftForSend(activeSession);
      if (!persisted) {
        return;
      }
      targetSession = persisted;
      createdFromDraft = persisted;
    }

    const previousMessages: PlaygroundMessageViewModel[] = [...targetSession.messages];
    const sessionId = targetSession.id;
    setError("");
    setIsSending(true);

    const shouldUseStreamingTransport = config.messaging.mode === "stream" || config.messaging.mode === "request";
    if (shouldUseStreamingTransport) {
      const userMessageId = createTransientMessageId("pending-user");
      const assistantMessageId = createTransientMessageId("pending-assistant");
      const initialStatus = {
        id: `${assistantMessageId}-thinking`,
        kind: "thinking",
        label: "Thinking",
        state: "running",
        started_at: new Date().toISOString(),
        completed_at: null,
        duration_ms: null,
        summary: null,
        details: {},
      };
      const optimisticMessages = updateTransientAssistantStatus(
        createOptimisticMessages(previousMessages, prompt, userMessageId, assistantMessageId),
        assistantMessageId,
        initialStatus,
      );
      const controller = new AbortController();
      streamAbortRef.current = controller;
      setDraft("");
      pinToBottomOnNextUpdate("smooth");
      setActiveSession((current) => (
        current && current.id === sessionId
          ? { ...current, messages: optimisticMessages }
          : current
      ));

      try {
        const streamOptions = {
          signal: controller.signal,
          onDelta: (text: string) => {
            setActiveSession((current) => (
              current && current.id === sessionId
                ? {
                  ...current,
                  messages: updateTransientAssistantMessage(current.messages, assistantMessageId, text),
                }
                : current
            ));
          },
          onStatus: (status: PlaygroundRunStatus) => {
            setActiveSession((current) => (
              current && current.id === sessionId
                ? {
                  ...current,
                  messages: updateTransientAssistantStatus(current.messages, assistantMessageId, status),
                }
                : current
            ));
          },
        };
        const result = isTemporarySession
          ? await streamTemporaryPlaygroundMessage(
            buildTemporaryMessagePayload(targetSession, prompt),
            token,
            streamOptions,
          )
          : await streamPlaygroundMessage(
            sessionId,
            { prompt },
            token,
            streamOptions,
          );
        const nextSession = mapPlaygroundSessionDetail(result.session);
        if (isTemporarySession) {
          setActiveSession({ ...nextSession, persistence: "temporary" });
        } else {
          setSavedSessions((existing) => upsertSession(existing, nextSession));
          setActiveSession(nextSession);
        }
      } catch (requestError) {
        if (controller.signal.aborted) {
          return;
        }
        if (draftSnapshot) {
          await restoreDraftAfterFailedFirstSend(draftSnapshot, createdFromDraft, prompt);
        } else {
          setActiveSession((current) => (
            current && current.id === sessionId
              ? { ...current, messages: previousMessages }
              : current
          ));
          setDraft(prompt);
        }
        showErrorFeedback(requestError, config.feedback.sendError);
      } finally {
        streamAbortRef.current = null;
        setIsSending(false);
      }
      return;
    }
  };

  return {
    createSession,
    createTemporaryChat,
    renameSession,
    deleteSession,
    sendPrompt,
    updateModel: async (sessionId: string, modelId: string): Promise<void> => {
      await updateSelectorState(
        sessionId,
        { model_selection: { model_id: modelId } },
        config.feedback.updateModelError,
      );
    },
    updateKnowledgeBase: async (sessionId: string, knowledgeBaseId: string): Promise<void> => {
      await updateSelectorState(
        sessionId,
        { knowledge_binding: { knowledge_base_id: knowledgeBaseId } },
        config.feedback.updateKnowledgeBaseError,
      );
    },
    updateAssistant: async (sessionId: string, assistantRef: string): Promise<void> => {
      await updateSelectorState(
        sessionId,
        { assistant_ref: assistantRef },
        config.feedback.updateAssistantError,
      );
    },
    abortActiveStream: (): void => {
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
      setIsSending(false);
    },
  };
}
