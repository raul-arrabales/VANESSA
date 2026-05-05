import type { PlaygroundWorkspaceConfig } from "../playgrounds/types";
import { VANESSA_CORE_ASSISTANT_EXPERIENCE } from "./assistantExperience";

export const vanessaCorePlaygroundConfig: PlaygroundWorkspaceConfig = {
  playgroundKind: VANESSA_CORE_ASSISTANT_EXPERIENCE.playground_kind,
  title: "Vanessa Core",
  panelAriaLabel: "Vanessa Core workspace",
  introText: "Chat with Vanessa in the Vanessa AI workspace.",
  loadingText: "Loading Vanessa conversation...",
  modelLoadingText: "Loading available models...",
  knowledgeBaseLoadingText: "Loading knowledge bases...",
  emptyStateText: "No messages yet. Start a Vanessa conversation to build the thread.",
  newSessionLabel: "New chat",
  emptySessionTitle: "Vanessa Core",
  temporarySessionLabel: "Temporary chat",
  temporarySessionTitle: "Temporary chat",
  draftPlaceholder: "Ask Vanessa anything",
  inlineSelectors: [],
  settingsSelectors: ["model"],
  messaging: {
    mode: "stream",
    submitLabel: "Send to Vanessa",
    busyLabel: "Vanessa is responding...",
    stopLabel: "Stop Vanessa response",
  },
  actions: {
    rename: true,
    delete: true,
  },
  sessionBootstrap: {
    mode: "saved-first",
    historyLoadingText: "Loading Vanessa sessions...",
  },
  prompts: {
    rename: "Rename Vanessa session",
    deleteConfirm: "Delete this Vanessa session?",
  },
  feedback: {
    createError: "Unable to create Vanessa session.",
    updateModelError: "Unable to update Vanessa model.",
    updateKnowledgeBaseError: "Unable to update Vanessa knowledge base.",
    updateAssistantError: "Unable to update Vanessa assistant.",
    renameError: "Unable to rename Vanessa session.",
    deleteError: "Unable to delete Vanessa session.",
    sendError: "Vanessa request failed.",
    optionsError: "Unable to load Vanessa workspace options.",
    sessionsError: "Unable to load Vanessa sessions.",
    sessionError: "Unable to load Vanessa session.",
    missingModel: "Model is required.",
    missingKnowledgeBase: "Knowledge base is required.",
  },
  defaultAssistantRef: VANESSA_CORE_ASSISTANT_EXPERIENCE.assistant_ref,
};
