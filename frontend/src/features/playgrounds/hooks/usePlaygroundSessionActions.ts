import type { Dispatch, SetStateAction } from "react";
import { useRef } from "react";
import {
  createPlaygroundSession,
  deletePlaygroundSession,
  sendPlaygroundMessage,
  streamPlaygroundMessage,
  updatePlaygroundSession,
} from "../../../api/playgrounds";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import type {
  PlaygroundMessageViewModel,
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
} from "../types";
import { mapPlaygroundSessionDetail, mapPlaygroundSessionSummary } from "../types";
import {
  createDraftSession,
  createOptimisticMessages,
  createTransientMessageId,
  removeSession,
  sortSessions,
  updateTransientAssistantMessage,
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

  const createOrResetDraftSession = (): PlaygroundSessionViewModel => {
    const nextDraft = createDraftSession(config, options, activeSession);
    setActiveSessionId(nextDraft.id);
    setActiveSession(nextDraft);
    setDraft("");
    setError("");
    return nextDraft;
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
            knowledge_base_id: config.selectors.knowledgeBase
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

    if (activeSession.persistence === "draft" && activeSession.id === sessionId) {
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

  const renameSession = async (sessionId: string): Promise<void> => {
    if (!token) {
      return;
    }

    const targetSession = savedSessions.find((session) => session.id === sessionId);
    if (!targetSession || targetSession.persistence === "draft") {
      return;
    }

    const nextTitle = window.prompt(config.prompts.rename, targetSession.title);
    if (nextTitle === null) {
      return;
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
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.renameError);
    } finally {
      setIsSessionBusy(false);
    }
  };

  const deleteSession = async (sessionId: string): Promise<void> => {
    if (!token) {
      return;
    }

    const targetSession = savedSessions.find((session) => session.id === sessionId);
    if (!targetSession || targetSession.persistence === "draft") {
      return;
    }
    if (!window.confirm(config.prompts.deleteConfirm)) {
      return;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      await deletePlaygroundSession(sessionId, token);
      const remaining = removeSession(savedSessions, sessionId);
      const isDeletingActiveSavedSession = activeSession?.id === sessionId && activeSession.persistence === "saved";

      if (!isDeletingActiveSavedSession) {
        setSavedSessions(sortSessions(remaining));
        return;
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
                knowledge_base_id: config.selectors.knowledgeBase
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
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.deleteError);
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
            knowledge_base_id: config.selectors.knowledgeBase
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
    if (config.selectors.knowledgeBase && !activeSession.selectorState.knowledgeBaseId) {
      setError(config.feedback.missingKnowledgeBase);
      return;
    }

    const prompt = draft.trim();
    const isDraftSession = activeSession.persistence === "draft";
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

    if (config.messaging.mode === "stream") {
      const userMessageId = createTransientMessageId("pending-user");
      const assistantMessageId = createTransientMessageId("pending-assistant");
      const optimisticMessages = createOptimisticMessages(previousMessages, prompt, userMessageId, assistantMessageId);
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
        const result = await streamPlaygroundMessage(
          sessionId,
          { prompt },
          token,
          {
            signal: controller.signal,
            onDelta: (text) => {
              setActiveSession((current) => (
                current && current.id === sessionId
                  ? {
                    ...current,
                    messages: updateTransientAssistantMessage(current.messages, assistantMessageId, text),
                  }
                  : current
              ));
            },
          },
        );
        const nextSession = mapPlaygroundSessionDetail(result.session);
        setSavedSessions((existing) => upsertSession(existing, nextSession));
        setActiveSession(nextSession);
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

    try {
      const result = await sendPlaygroundMessage(
        sessionId,
        { prompt },
        token,
      );
      const nextSession = mapPlaygroundSessionDetail(result.session);
      setSavedSessions((existing) => upsertSession(existing, nextSession));
      setActiveSession(nextSession);
      setDraft("");
      pinToBottomOnNextUpdate("smooth");
    } catch (requestError) {
      if (draftSnapshot) {
        await restoreDraftAfterFailedFirstSend(draftSnapshot, createdFromDraft, prompt);
      } else {
        setDraft(prompt);
      }
      showErrorFeedback(requestError, config.feedback.sendError);
    } finally {
      setIsSending(false);
    }
  };

  return {
    createSession,
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
    },
  };
}
