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
  const hasLoadedRequiredOptions = optionsState.hasLoadedModels
    && (!config.selectors.knowledgeBase || optionsState.hasLoadedKnowledgeBases);
  const isRequiredOptionsLoading = optionsState.isModelsLoading
    || (config.selectors.knowledgeBase && optionsState.isKnowledgeBasesLoading);
  const sessionState = usePlaygroundSessions({
    token,
    isAuthenticated,
    isOptionsLoading: isRequiredOptionsLoading,
    hasLoadedOptions: hasLoadedRequiredOptions,
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
    savedSessions: sessionState.savedSessions,
    setSavedSessions: sessionState.setSavedSessions,
    activeSession: sessionState.activeSession,
    setActiveSession: sessionState.setActiveSession,
    setActiveSessionId: sessionState.setActiveSessionId,
    setError: sessionState.setActiveError,
    setIsSending,
    setIsSessionBusy,
    pinToBottomOnNextUpdate,
  });
  abortActiveStreamRef.current = actions.abortActiveStream;

  useEffect(() => () => {
    abortActiveStreamRef.current();
  }, []);

  const isInteractionLocked = isSending || isSessionBusy;
  const activeSession = sessionState.activeSession;
  const modelAvailabilityMessage = optionsState.modelError
    || (optionsState.hasLoadedModels && optionsState.models.length === 0
      ? "No enabled models are available right now."
      : "");
  const knowledgeBaseAvailabilityMessage = config.selectors.knowledgeBase
    ? (
      optionsState.knowledgeBaseError
      || (
        optionsState.hasLoadedKnowledgeBases && optionsState.knowledgeBases.length === 0
          ? (optionsState.configurationMessage || "No knowledge bases are available right now.")
          : ""
      )
    )
    : "";
  const hasUsableModels = optionsState.hasLoadedModels && !optionsState.modelError && optionsState.models.length > 0;
  const hasUsableKnowledgeBases = !config.selectors.knowledgeBase
    || (
      optionsState.hasLoadedKnowledgeBases
      && !optionsState.knowledgeBaseError
      && optionsState.knowledgeBases.length > 0
    );
  const composerError = sessionState.activeError;
  const isWorkspaceReady = Boolean(activeSession) && hasUsableModels && hasUsableKnowledgeBases;
  const threadStatusText = sessionState.isActiveSessionLoading
    ? config.loadingText
    : !optionsState.hasLoadedModels
      ? config.modelLoadingText
      : modelAvailabilityMessage
        ? modelAvailabilityMessage
      : config.selectors.knowledgeBase && !optionsState.hasLoadedKnowledgeBases
        ? config.knowledgeBaseLoadingText
        : knowledgeBaseAvailabilityMessage
          ? knowledgeBaseAvailabilityMessage
        : config.loadingText;

  return (
    <section
      className="panel chatbot-shell"
      aria-label={config.panelAriaLabel}
      data-history-collapsed={preferences.isSidebarCollapsed ? "true" : "false"}
    >
      <SessionSidebar
        title={config.title}
        introText={config.introText}
        historyLoadingText={config.sessionBootstrap.historyLoadingText}
        newSessionLabel={config.newSessionLabel}
        sessions={sessionState.savedSessions}
        activeSessionId={sessionState.activeSessionId}
        canCreateSession={sessionState.canCreateSession}
        isInteractionLocked={isInteractionLocked || sessionState.isActiveSessionLoading}
        isCollapsed={preferences.isSidebarCollapsed}
        isHistoryLoading={sessionState.isHistoryLoading}
        historyError={sessionState.historyError}
        onToggleCollapsed={preferences.toggleSidebar}
        onCreateSession={() => void actions.createSession()}
        onSelectSession={(sessionId) => {
          pinToBottomOnNextUpdate("auto");
          sessionState.setActiveSessionId(sessionId);
          sessionState.setActiveSession(null);
          sessionState.setActiveError("");
        }}
        onRenameSession={(sessionId) => void actions.renameSession(sessionId)}
        onDeleteSession={(sessionId) => void actions.deleteSession(sessionId)}
        canRenameSession={config.actions.rename}
        canDeleteSession={config.actions.delete}
      />

      <div className="chatbot-main card-stack">
        <div className="chatbot-sidebar-header">
          <h3 className="section-title">{activeSession?.title ?? config.emptySessionTitle}</h3>
        </div>

        {config.selectors.model ? (
          <ModelSelector
            models={optionsState.models}
            value={activeSession?.selectorState.modelId ?? ""}
            isLoading={!optionsState.hasLoadedModels}
            disabled={!activeSession || !hasUsableModels || isSending}
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
                disabled={!activeSession || !hasUsableModels || isSending}
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
                disabled={!activeSession || !optionsState.hasLoadedKnowledgeBases || optionsState.knowledgeBases.length === 0 || isSending}
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
          isBootstrapping={!isWorkspaceReady || sessionState.isActiveSessionLoading}
          loadingText={threadStatusText}
          emptyStateText={config.emptyStateText}
          threadRef={threadRef}
          handleScroll={handleScroll}
          hasUnreadContentBelow={hasUnreadContentBelow}
          isPinnedToBottom={isPinnedToBottom}
          scrollToBottom={scrollToBottom}
        />

        <Composer
          draft={preferences.draft}
          error={composerError}
          disabled={isSending || !isWorkspaceReady}
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
