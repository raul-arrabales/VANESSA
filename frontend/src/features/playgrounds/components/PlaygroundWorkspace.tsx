import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../../../auth/AuthProvider";
import { useStickyChatScroll } from "../../../hooks/useStickyChatScroll";
import AssistantSelector from "./AssistantSelector";
import Composer from "./Composer";
import KnowledgeBaseSelector from "./KnowledgeBaseSelector";
import ModelSelector from "./ModelSelector";
import SessionSidebar from "./SessionSidebar";
import ThreadPanel from "./ThreadPanel";
import { usePlaygroundOptions } from "../hooks/usePlaygroundOptions";
import { usePlaygroundPreferences } from "../hooks/usePlaygroundPreferences";
import { usePlaygroundSessionActions } from "../hooks/usePlaygroundSessionActions";
import { usePlaygroundSessions } from "../hooks/usePlaygroundSessions";
import type { PlaygroundWorkspaceConfig } from "../types";

type PlaygroundWorkspaceProps = {
  config: PlaygroundWorkspaceConfig;
};

export default function PlaygroundWorkspace({ config }: PlaygroundWorkspaceProps): JSX.Element {
  const { token, isAuthenticated } = useAuth();
  const preferences = usePlaygroundPreferences(config.playgroundKind);
  const optionsState = usePlaygroundOptions({
    token,
    isAuthenticated,
    config,
  });
  const sessionState = usePlaygroundSessions({
    token,
    isAuthenticated,
    isOptionsLoading: optionsState.isLoading,
    hasLoadedOptions: optionsState.hasLoaded,
    config,
    options: {
      models: optionsState.models,
      assistants: optionsState.assistants,
      knowledgeBases: optionsState.knowledgeBases,
      defaultAssistantRef: optionsState.defaultAssistantRef,
      defaultKnowledgeBaseId: optionsState.defaultKnowledgeBaseId,
      configurationMessage: optionsState.configurationMessage,
    },
  });
  const [isSending, setIsSending] = useState(false);
  const [isSessionBusy, setIsSessionBusy] = useState(false);
  const abortActiveStreamRef = useRef<() => void>(() => undefined);

  const threadVersion = useMemo(() => {
    if (!sessionState.activeSession) {
      return "empty";
    }

    return `${sessionState.activeSession.id}:${sessionState.activeSession.messages.map((message) => (
      `${message.id}:${message.content.length}`
    )).join("|")}`;
  }, [sessionState.activeSession]);
  const {
    threadRef,
    isPinnedToBottom,
    hasUnreadContentBelow,
    handleScroll,
    scrollToBottom,
    pinToBottomOnNextUpdate,
  } = useStickyChatScroll(threadVersion);

  const actions = usePlaygroundSessionActions({
    token,
    config,
    options: {
      models: optionsState.models,
      assistants: optionsState.assistants,
      knowledgeBases: optionsState.knowledgeBases,
      defaultAssistantRef: optionsState.defaultAssistantRef,
      defaultKnowledgeBaseId: optionsState.defaultKnowledgeBaseId,
      configurationMessage: optionsState.configurationMessage,
    },
    draft: preferences.draft,
    setDraft: preferences.setDraft,
    sessions: sessionState.sessions,
    setSessions: sessionState.setSessions,
    activeSession: sessionState.activeSession,
    setActiveSession: sessionState.setActiveSession,
    setActiveSessionId: sessionState.setActiveSessionId,
    setError: sessionState.setError,
    setIsSending,
    setIsSessionBusy,
    pinToBottomOnNextUpdate,
  });
  abortActiveStreamRef.current = actions.abortActiveStream;

  useEffect(() => () => {
    abortActiveStreamRef.current();
  }, []);

  const isInteractionLocked = isSending || isSessionBusy;
  const combinedError = sessionState.error || optionsState.error;
  const activeSession = sessionState.activeSession;

  const headerToolbar = useMemo(() => (
    <div className="chatbot-actions">
      {config.actions.rename ? (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => void actions.renameSession()}
          disabled={!activeSession || isInteractionLocked}
        >
          Rename
        </button>
      ) : null}
      {config.actions.delete ? (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => void actions.deleteSession()}
          disabled={!activeSession || isInteractionLocked}
        >
          Delete
        </button>
      ) : null}
    </div>
  ), [actions, activeSession, config.actions.delete, config.actions.rename, isInteractionLocked]);

  return (
    <section className="panel chatbot-shell" aria-label={config.panelAriaLabel}>
      <SessionSidebar
        title={config.title}
        introText={config.introText}
        newSessionLabel={config.newSessionLabel}
        sessions={sessionState.sessions}
        activeSessionId={sessionState.activeSessionId}
        canCreateSession={sessionState.canCreateSession && !optionsState.isLoading}
        isInteractionLocked={isInteractionLocked || sessionState.isBootstrapping}
        isCollapsed={preferences.isSidebarCollapsed}
        onToggleCollapsed={preferences.toggleSidebar}
        onCreateSession={() => void actions.createSession()}
        onSelectSession={(sessionId) => {
          pinToBottomOnNextUpdate("auto");
          sessionState.setActiveSessionId(sessionId);
          sessionState.setActiveSession(null);
        }}
      />

      <div className="chatbot-main card-stack">
        <div className="chatbot-sidebar-header">
          <h3 className="section-title">{activeSession?.title ?? config.emptySessionTitle}</h3>
          {headerToolbar}
        </div>

        {config.selectors.model ? (
          <ModelSelector
            models={optionsState.models}
            value={activeSession?.selectorState.modelId ?? ""}
            disabled={optionsState.models.length === 0 || !activeSession || isSending}
            onChange={(value) => {
              if (activeSession) {
                void actions.updateModel(activeSession.id, value);
              }
            }}
          />
        ) : null}

        {config.selectors.assistant || config.selectors.knowledgeBase ? (
          <div className="chatbot-toolbar">
            {config.selectors.assistant ? (
              <AssistantSelector
                assistants={optionsState.assistants}
                value={activeSession?.selectorState.assistantRef ?? optionsState.defaultAssistantRef ?? ""}
                disabled={!activeSession || isSending}
                onChange={(value) => {
                  if (activeSession) {
                    void actions.updateAssistant(activeSession.id, value);
                  }
                }}
              />
            ) : null}
            {config.selectors.knowledgeBase ? (
              <KnowledgeBaseSelector
                knowledgeBases={optionsState.knowledgeBases}
                value={activeSession?.selectorState.knowledgeBaseId ?? ""}
                disabled={!activeSession || isSending}
                onChange={(value) => {
                  if (activeSession) {
                    void actions.updateKnowledgeBase(activeSession.id, value);
                  }
                }}
              />
            ) : null}
          </div>
        ) : null}

        <ThreadPanel
          activeSession={activeSession}
          isBootstrapping={sessionState.isBootstrapping || optionsState.isLoading}
          loadingText={config.loadingText}
          emptyStateText={config.emptyStateText}
          threadRef={threadRef}
          handleScroll={handleScroll}
          hasUnreadContentBelow={hasUnreadContentBelow}
          isPinnedToBottom={isPinnedToBottom}
          scrollToBottom={scrollToBottom}
        />

        <Composer
          draft={preferences.draft}
          error={combinedError}
          disabled={isSending}
          submitLabel={config.messaging.submitLabel}
          busyLabel={config.messaging.busyLabel}
          isSending={isSending}
          placeholder={config.draftPlaceholder}
          onDraftChange={preferences.setDraft}
          onSubmit={() => void actions.sendPrompt()}
        />
      </div>
    </section>
  );
}
