import { useMemo } from "react";
import type {
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
} from "../types";

type PlaygroundWorkspaceOptionsState = PlaygroundWorkspaceOptions & {
  modelError: string;
  knowledgeBaseError: string;
  hasLoadedModels: boolean;
  hasLoadedKnowledgeBases: boolean;
};

type PlaygroundWorkspaceSessionState = {
  activeSession: PlaygroundSessionViewModel | null;
  activeError: string;
  isActiveSessionLoading: boolean;
};

export type UsePlaygroundWorkspaceViewStateParams = {
  config: PlaygroundWorkspaceConfig;
  optionsState: PlaygroundWorkspaceOptionsState;
  sessionState: PlaygroundWorkspaceSessionState;
  isSending: boolean;
  isSessionBusy: boolean;
};

export type PlaygroundWorkspaceViewState = {
  activeSession: PlaygroundSessionViewModel | null;
  composerError: string;
  isInteractionLocked: boolean;
  isWorkspaceReady: boolean;
  isThreadBootstrapping: boolean;
  threadStatusText: string;
  hasUsableModels: boolean;
  hasUsableKnowledgeBases: boolean;
  modelAvailabilityMessage: string;
  knowledgeBaseAvailabilityMessage: string;
  isModelSelectorDisabled: boolean;
  isAssistantSelectorDisabled: boolean;
  isKnowledgeBaseSelectorDisabled: boolean;
  isSidebarInteractionLocked: boolean;
};

export function buildPlaygroundWorkspaceViewState({
  config,
  optionsState,
  sessionState,
  isSending,
  isSessionBusy,
}: UsePlaygroundWorkspaceViewStateParams): PlaygroundWorkspaceViewState {
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
  const isWorkspaceReady = Boolean(activeSession) && hasUsableModels && hasUsableKnowledgeBases;
  const threadStatusText = sessionState.isActiveSessionLoading
    ? config.loadingText
    : !optionsState.hasLoadedModels
      ? config.modelLoadingText
      : modelAvailabilityMessage
        ? modelAvailabilityMessage
        : config.selectors.knowledgeBase && !optionsState.hasLoadedKnowledgeBases
          ? config.knowledgeBaseLoadingText
          : knowledgeBaseAvailabilityMessage || config.loadingText;
  const isInteractionLocked = isSending || isSessionBusy;

  return {
    activeSession,
    composerError: sessionState.activeError,
    isInteractionLocked,
    isWorkspaceReady,
    isThreadBootstrapping: !isWorkspaceReady || sessionState.isActiveSessionLoading,
    threadStatusText,
    hasUsableModels,
    hasUsableKnowledgeBases,
    modelAvailabilityMessage,
    knowledgeBaseAvailabilityMessage,
    isModelSelectorDisabled: !activeSession || !hasUsableModels || isSending,
    isAssistantSelectorDisabled: !activeSession || !hasUsableModels || isSending,
    isKnowledgeBaseSelectorDisabled: !activeSession
      || !optionsState.hasLoadedKnowledgeBases
      || optionsState.knowledgeBases.length === 0
      || isSending,
    isSidebarInteractionLocked: isInteractionLocked || sessionState.isActiveSessionLoading,
  };
}

export function usePlaygroundWorkspaceViewState(
  params: UsePlaygroundWorkspaceViewStateParams,
): PlaygroundWorkspaceViewState {
  return useMemo(() => buildPlaygroundWorkspaceViewState(params), [params]);
}
