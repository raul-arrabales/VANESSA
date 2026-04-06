import { describe, expect, it } from "vitest";
import { knowledgePlaygroundConfig, chatPlaygroundConfig } from "../configs";
import { buildPlaygroundWorkspaceViewState } from "./usePlaygroundWorkspaceViewState";
import type { PlaygroundSessionViewModel, PlaygroundWorkspaceOptions } from "../types";

function buildOptionsState(
  overrides: Partial<PlaygroundWorkspaceOptions & {
    modelError: string;
    knowledgeBaseError: string;
    hasLoadedModels: boolean;
    hasLoadedKnowledgeBases: boolean;
  }> = {},
) {
  return {
    models: [{ id: "safe-small", displayName: "Safe Small" }],
    assistants: [],
    knowledgeBases: [],
    defaultAssistantRef: null,
    defaultKnowledgeBaseId: null,
    configurationMessage: "",
    modelError: "",
    knowledgeBaseError: "",
    hasLoadedModels: true,
    hasLoadedKnowledgeBases: true,
    ...overrides,
  };
}

function buildSession(
  overrides: Partial<PlaygroundSessionViewModel> = {},
): PlaygroundSessionViewModel {
  return {
    id: "sess-1",
    playgroundKind: "chat",
    title: "Conversation",
    titleSource: "auto",
    selectorState: {
      assistantRef: null,
      modelId: "safe-small",
      knowledgeBaseId: null,
    },
    messageCount: 0,
    createdAt: null,
    updatedAt: null,
    messages: [],
    persistence: "draft",
    ...overrides,
  };
}

function buildSessionState(overrides: Partial<{
  activeSession: PlaygroundSessionViewModel | null;
  activeError: string;
  isActiveSessionLoading: boolean;
}> = {}) {
  return {
    activeSession: buildSession(),
    activeError: "",
    isActiveSessionLoading: false,
    ...overrides,
  };
}

describe("buildPlaygroundWorkspaceViewState", () => {
  it("shows model loading before chat models are ready", () => {
    const result = buildPlaygroundWorkspaceViewState({
      config: chatPlaygroundConfig,
      optionsState: buildOptionsState({
        models: [],
        hasLoadedModels: false,
      }),
      sessionState: buildSessionState(),
      isSending: false,
      isSessionBusy: false,
    });

    expect(result.threadStatusText).toBe("Loading available models...");
    expect(result.isWorkspaceReady).toBe(false);
    expect(result.isModelSelectorDisabled).toBe(true);
    expect(result.isThreadBootstrapping).toBe(true);
  });

  it("shows the empty-model blocker only after model loading completes with no models", () => {
    const result = buildPlaygroundWorkspaceViewState({
      config: chatPlaygroundConfig,
      optionsState: buildOptionsState({
        models: [],
      }),
      sessionState: buildSessionState(),
      isSending: false,
      isSessionBusy: false,
    });

    expect(result.modelAvailabilityMessage).toBe("No enabled models are available right now.");
    expect(result.threadStatusText).toBe("No enabled models are available right now.");
    expect(result.isWorkspaceReady).toBe(false);
  });

  it("shows knowledge-base loading after models are ready but KBs are still pending", () => {
    const result = buildPlaygroundWorkspaceViewState({
      config: knowledgePlaygroundConfig,
      optionsState: buildOptionsState({
        knowledgeBases: [],
        hasLoadedKnowledgeBases: false,
      }),
      sessionState: buildSessionState({
        activeSession: buildSession({
          playgroundKind: "knowledge",
          selectorState: {
            assistantRef: null,
            modelId: "safe-small",
            knowledgeBaseId: null,
          },
        }),
      }),
      isSending: false,
      isSessionBusy: false,
    });

    expect(result.threadStatusText).toBe("Loading knowledge bases...");
    expect(result.isKnowledgeBaseSelectorDisabled).toBe(true);
    expect(result.isWorkspaceReady).toBe(false);
  });

  it("shows the KB configuration blocker when no knowledge bases are available", () => {
    const result = buildPlaygroundWorkspaceViewState({
      config: knowledgePlaygroundConfig,
      optionsState: buildOptionsState({
        knowledgeBases: [],
        configurationMessage: "Knowledge bases are not configured.",
      }),
      sessionState: buildSessionState({
        activeSession: buildSession({
          playgroundKind: "knowledge",
          selectorState: {
            assistantRef: null,
            modelId: "safe-small",
            knowledgeBaseId: null,
          },
        }),
      }),
      isSending: false,
      isSessionBusy: false,
    });

    expect(result.knowledgeBaseAvailabilityMessage).toBe("Knowledge bases are not configured.");
    expect(result.threadStatusText).toBe("Knowledge bases are not configured.");
    expect(result.isWorkspaceReady).toBe(false);
    expect(result.isKnowledgeBaseSelectorDisabled).toBe(true);
  });

  it("preserves the active-session loading copy and sidebar lock while a saved session is loading", () => {
    const result = buildPlaygroundWorkspaceViewState({
      config: chatPlaygroundConfig,
      optionsState: buildOptionsState(),
      sessionState: buildSessionState({
        isActiveSessionLoading: true,
        activeError: "Session load failed.",
      }),
      isSending: false,
      isSessionBusy: true,
    });

    expect(result.threadStatusText).toBe(chatPlaygroundConfig.loadingText);
    expect(result.composerError).toBe("Session load failed.");
    expect(result.isInteractionLocked).toBe(true);
    expect(result.isSidebarInteractionLocked).toBe(true);
    expect(result.isThreadBootstrapping).toBe(true);
  });
});
