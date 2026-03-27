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
  sessions: PlaygroundSessionViewModel[];
  setSessions: Dispatch<SetStateAction<PlaygroundSessionViewModel[]>>;
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
  sessions,
  setSessions,
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

  const createSession = async (): Promise<void> => {
    if (!token) {
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
      setSessions((existing) => upsertSession(existing, nextSession));
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
    if (!token) {
      return;
    }

    setError("");
    try {
      const updated = await updatePlaygroundSession(sessionId, payload, token);
      const updatedViewModel = mapPlaygroundSessionSummary(updated);
      setSessions((existing) => upsertSession(existing, updatedViewModel));
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

  const renameSession = async (): Promise<void> => {
    if (!token || !activeSession) {
      return;
    }

    const nextTitle = window.prompt(config.prompts.rename, activeSession.title);
    if (nextTitle === null) {
      return;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      const updated = await updatePlaygroundSession(activeSession.id, { title: nextTitle }, token);
      const updatedViewModel = mapPlaygroundSessionSummary(updated);
      setSessions((existing) => upsertSession(existing, updatedViewModel));
      setActiveSession((current) => (
        current && current.id === updatedViewModel.id
          ? { ...current, ...updatedViewModel, messages: current.messages }
          : current
      ));
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.renameError);
    } finally {
      setIsSessionBusy(false);
    }
  };

  const deleteSession = async (): Promise<void> => {
    if (!token || !activeSession) {
      return;
    }
    if (!window.confirm(config.prompts.deleteConfirm)) {
      return;
    }

    setError("");
    setIsSessionBusy(true);
    try {
      await deletePlaygroundSession(activeSession.id, token);
      const remaining = removeSession(sessions, activeSession.id);
      if (remaining.length === 0) {
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
        setSessions([nextSession]);
        setActiveSessionId(nextSession.id);
        setActiveSession(nextSession);
      } else {
        const sorted = sortSessions(remaining);
        setSessions(sorted);
        setActiveSessionId(sorted[0]?.id ?? null);
        setActiveSession(null);
      }
    } catch (requestError) {
      showErrorFeedback(requestError, config.feedback.deleteError);
    } finally {
      setIsSessionBusy(false);
    }
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
    const previousMessages: PlaygroundMessageViewModel[] = [...activeSession.messages];
    const sessionId = activeSession.id;
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
        setSessions((existing) => upsertSession(existing, nextSession));
        setActiveSession(nextSession);
      } catch (requestError) {
        if (controller.signal.aborted) {
          return;
        }
        setActiveSession((current) => (
          current && current.id === sessionId
            ? { ...current, messages: previousMessages }
            : current
        ));
        setDraft(prompt);
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
      setSessions((existing) => upsertSession(existing, nextSession));
      setActiveSession(nextSession);
      setDraft("");
      pinToBottomOnNextUpdate("smooth");
    } catch (requestError) {
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
