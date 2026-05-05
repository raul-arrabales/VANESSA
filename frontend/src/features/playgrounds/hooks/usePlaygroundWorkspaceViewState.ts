import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type {
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
} from "../types";
import { hasSelector } from "../selectorConfig";

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
  localizedMessages?: {
    noEnabledModels: string;
    noKnowledgeBases: string;
  };
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
  localizedMessages,
}: UsePlaygroundWorkspaceViewStateParams): PlaygroundWorkspaceViewState {
  const activeSession = sessionState.activeSession;
  const hasKnowledgeBaseSelector = hasSelector(config, "knowledgeBase");
  const modelAvailabilityMessage = optionsState.modelError
    || (optionsState.hasLoadedModels && optionsState.models.length === 0
      ? (localizedMessages?.noEnabledModels ?? "")
      : "");
  const knowledgeBaseAvailabilityMessage = hasKnowledgeBaseSelector
    ? (
      optionsState.knowledgeBaseError
      || (
        optionsState.hasLoadedKnowledgeBases && optionsState.knowledgeBases.length === 0
          ? (optionsState.configurationMessage || localizedMessages?.noKnowledgeBases || "")
          : ""
      )
    )
    : "";
  const hasUsableModels = optionsState.hasLoadedModels && !optionsState.modelError && optionsState.models.length > 0;
  const hasUsableKnowledgeBases = !hasKnowledgeBaseSelector
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
        : hasKnowledgeBaseSelector && !optionsState.hasLoadedKnowledgeBases
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
  const { t } = useTranslation("common");

  return useMemo(() => buildPlaygroundWorkspaceViewState({
    ...params,
    localizedMessages: {
      noEnabledModels: t("playgrounds.shared.noEnabledModels"),
      noKnowledgeBases: t("playgrounds.shared.noKnowledgeBases"),
    },
  }), [params, t]);
}
