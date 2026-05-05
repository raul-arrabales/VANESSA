import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
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
import { usePlaygroundWorkspaceViewState } from "../hooks/usePlaygroundWorkspaceViewState";
import type { PlaygroundWorkspaceConfig } from "../types";

type PlaygroundWorkspaceProps = {
  config: PlaygroundWorkspaceConfig;
};

export default function PlaygroundWorkspace({ config }: PlaygroundWorkspaceProps): JSX.Element {
  const { t } = useTranslation("common");
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
  const [isSettingsDialogOpen, setIsSettingsDialogOpen] = useState(false);
  const [pendingDialog, setPendingDialog] = useState<{ kind: "rename" | "delete"; sessionId: string; title: string } | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [isDialogSubmitting, setIsDialogSubmitting] = useState(false);
  const [composerHeight, setComposerHeight] = useState(96);
  const abortActiveStreamRef = useRef<() => void>(() => undefined);
  const settingsModelSelectRef = useRef<HTMLSelectElement>(null);
  const settingsKnowledgeBaseSelectRef = useRef<HTMLSelectElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

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

  useEffect(() => {
    if (!pendingDialog) {
      return;
    }
    if (!sessionState.savedSessions.some((session) => session.id === pendingDialog.sessionId)) {
      setPendingDialog(null);
      setRenameValue("");
      setIsDialogSubmitting(false);
    }
  }, [pendingDialog, sessionState.savedSessions]);

  const viewState = usePlaygroundWorkspaceViewState({
    config,
    optionsState,
    sessionState,
    isSending,
    isSessionBusy,
  });
  const hasSettingsSelectors = config.selectors.model || config.selectors.knowledgeBase;
  const settingsInitialFocusRef = config.selectors.model ? settingsModelSelectRef : settingsKnowledgeBaseSelectRef;

  return (
    <section
      className="chatbot-shell"
      aria-label={config.panelAriaLabel}
      data-history-collapsed={preferences.isSidebarCollapsed ? "true" : "false"}
    >
      <SessionSidebar
        title={config.title}
        introText={config.introText}
        historyLoadingText={config.sessionBootstrap.historyLoadingText}
        newSessionLabel={config.newSessionLabel}
        temporarySessionLabel={config.temporarySessionLabel}
        settingsLabel={t("playgroundSessionSidebar.settings")}
        showSettings={hasSettingsSelectors}
        sessions={sessionState.savedSessions}
        activeSessionId={sessionState.activeSessionId}
        canCreateSession={sessionState.canCreateSession}
        isInteractionLocked={viewState.isSidebarInteractionLocked}
        isCollapsed={preferences.isSidebarCollapsed}
        isHistoryLoading={sessionState.isHistoryLoading}
        historyError={sessionState.historyError}
        onToggleCollapsed={preferences.toggleSidebar}
        onCreateSession={() => void actions.createSession()}
        onCreateTemporarySession={() => {
          pinToBottomOnNextUpdate("auto");
          actions.createTemporaryChat();
        }}
        onOpenSettings={() => setIsSettingsDialogOpen(true)}
        onSelectSession={(sessionId) => {
          pinToBottomOnNextUpdate("auto");
          sessionState.setActiveSessionId(sessionId);
          sessionState.setActiveSession(null);
          sessionState.setActiveError("");
        }}
        onRenameSession={(sessionId) => {
          const targetSession = sessionState.savedSessions.find((session) => session.id === sessionId);
          if (!targetSession) {
            return;
          }
          setPendingDialog({ kind: "rename", sessionId, title: targetSession.title });
          setRenameValue(targetSession.title);
          setIsDialogSubmitting(false);
        }}
        onDeleteSession={(sessionId) => {
          const targetSession = sessionState.savedSessions.find((session) => session.id === sessionId);
          if (!targetSession) {
            return;
          }
          setPendingDialog({ kind: "delete", sessionId, title: targetSession.title });
          setRenameValue("");
          setIsDialogSubmitting(false);
        }}
        canRenameSession={config.actions.rename}
        canDeleteSession={config.actions.delete}
      />

      <div className="chatbot-main">
        <div className="chatbot-sidebar-header">
          <h3 className="section-title">{viewState.activeSession?.title ?? config.emptySessionTitle}</h3>
        </div>

        {config.selectors.assistant ? (
          <div className="chatbot-toolbar">
            {config.selectors.assistant ? (
              <AssistantSelector
                assistants={optionsState.assistants}
                value={viewState.activeSession?.selectorState.assistantRef ?? optionsState.defaultAssistantRef ?? ""}
                disabled={viewState.isAssistantSelectorDisabled}
                onChange={(value) => {
                  if (viewState.activeSession) {
                    void actions.updateAssistant(viewState.activeSession.id, value);
                  }
                }}
              />
            ) : null}
          </div>
        ) : null}

        <ThreadPanel
          activeSession={viewState.activeSession}
          isBootstrapping={viewState.isThreadBootstrapping}
          loadingText={viewState.threadStatusText}
          emptyStateText={config.emptyStateText}
          threadRef={threadRef}
          handleScroll={handleScroll}
          hasUnreadContentBelow={hasUnreadContentBelow}
          isPinnedToBottom={isPinnedToBottom}
          scrollToBottom={scrollToBottom}
          composerHeight={composerHeight}
          composer={(
            <Composer
              draft={preferences.draft}
              error={viewState.composerError}
              disabled={!viewState.isWorkspaceReady}
              submitLabel={config.messaging.submitLabel}
              busyLabel={config.messaging.busyLabel}
              stopLabel={config.messaging.stopLabel}
              isSending={isSending}
              canStop={config.messaging.mode === "stream" && isSending}
              placeholder={config.draftPlaceholder}
              onDraftChange={preferences.setDraft}
              onSubmit={() => void actions.sendPrompt()}
              onCancel={actions.abortActiveStream}
              onHeightChange={(height) => {
                if (height > 0) {
                  setComposerHeight(height);
                }
              }}
            />
          )}
        />
      </div>
      {isSettingsDialogOpen && hasSettingsSelectors ? (
        <ModalDialog
          className="playground-session-dialog"
          title={t("playgroundSessionSettings.title")}
          description={t("playgroundSessionSettings.description")}
          onClose={() => setIsSettingsDialogOpen(false)}
          initialFocusRef={settingsInitialFocusRef}
          actions={(
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsSettingsDialogOpen(false)}
            >
              {t("playgroundSessionSettings.close")}
            </button>
          )}
        >
          <div className="control-group playground-session-settings-fields">
            {config.selectors.model ? (
              <ModelSelector
                selectRef={settingsModelSelectRef}
                models={optionsState.models}
                value={viewState.activeSession?.selectorState.modelId ?? ""}
                isLoading={!optionsState.hasLoadedModels}
                disabled={viewState.isModelSelectorDisabled}
                onChange={(value) => {
                  if (viewState.activeSession) {
                    void actions.updateModel(viewState.activeSession.id, value);
                  }
                }}
              />
            ) : null}
            {config.selectors.knowledgeBase ? (
              <KnowledgeBaseSelector
                selectRef={settingsKnowledgeBaseSelectRef}
                knowledgeBases={optionsState.knowledgeBases}
                value={viewState.activeSession?.selectorState.knowledgeBaseId ?? ""}
                isLoading={!optionsState.hasLoadedKnowledgeBases}
                disabled={viewState.isKnowledgeBaseSelectorDisabled}
                onChange={(value) => {
                  if (viewState.activeSession) {
                    void actions.updateKnowledgeBase(viewState.activeSession.id, value);
                  }
                }}
              />
            ) : null}
          </div>
        </ModalDialog>
      ) : null}
      {pendingDialog?.kind === "rename" ? (
        <ModalDialog
          className="playground-session-dialog"
          eyebrow={t("playgroundSessionDialogs.rename.eyebrow")}
          title={t("playgroundSessionDialogs.rename.title")}
          description={t("playgroundSessionDialogs.rename.description")}
          onClose={() => {
            if (!isDialogSubmitting) {
              setPendingDialog(null);
              setRenameValue("");
            }
          }}
          closeDisabled={isDialogSubmitting}
          initialFocusRef={renameInputRef}
          actions={(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setPendingDialog(null);
                  setRenameValue("");
                }}
                disabled={isDialogSubmitting}
              >
                {t("playgroundSessionDialogs.cancel")}
              </button>
              <button
                ref={confirmButtonRef}
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  const nextTitle = renameValue.trim();
                  if (!nextTitle) {
                    return;
                  }
                  setIsDialogSubmitting(true);
                  void actions.renameSession(pendingDialog.sessionId, nextTitle)
                    .then((didRename) => {
                      if (didRename) {
                        setPendingDialog(null);
                        setRenameValue("");
                      }
                    })
                    .finally(() => {
                      setIsDialogSubmitting(false);
                    });
                }}
                disabled={isDialogSubmitting || !renameValue.trim()}
              >
                {t("playgroundSessionDialogs.rename.confirm")}
              </button>
            </>
          )}
        >
          <label className="control-group">
            <span className="field-label">{t("playgroundSessionDialogs.rename.fieldLabel")}</span>
            <input
              ref={renameInputRef}
              className="field-input"
              value={renameValue}
              onChange={(event) => setRenameValue(event.currentTarget.value)}
              disabled={isDialogSubmitting}
            />
          </label>
        </ModalDialog>
      ) : null}
      {pendingDialog?.kind === "delete" ? (
        <ModalDialog
          className="playground-session-dialog"
          eyebrow={t("playgroundSessionDialogs.delete.eyebrow")}
          title={t("playgroundSessionDialogs.delete.title")}
          description={t("playgroundSessionDialogs.delete.description", { title: pendingDialog.title })}
          onClose={() => {
            if (!isDialogSubmitting) {
              setPendingDialog(null);
            }
          }}
          closeDisabled={isDialogSubmitting}
          initialFocusRef={confirmButtonRef}
          actions={(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setPendingDialog(null)}
                disabled={isDialogSubmitting}
              >
                {t("playgroundSessionDialogs.cancel")}
              </button>
              <button
                ref={confirmButtonRef}
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setIsDialogSubmitting(true);
                  void actions.deleteSession(pendingDialog.sessionId)
                    .then((didDelete) => {
                      if (didDelete) {
                        setPendingDialog(null);
                      }
                    })
                    .finally(() => {
                      setIsDialogSubmitting(false);
                    });
                }}
                disabled={isDialogSubmitting}
              >
                {t("playgroundSessionDialogs.delete.confirm")}
              </button>
            </>
          )}
        />
      ) : null}
    </section>
  );
}
