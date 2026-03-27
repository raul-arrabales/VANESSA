import type { PlaygroundWorkspaceConfig } from "../playgrounds/types";
import { VANESSA_CORE_ASSISTANT_EXPERIENCE } from "./assistantExperience";

export const vanessaCorePlaygroundConfig: PlaygroundWorkspaceConfig = {
  playgroundKind: VANESSA_CORE_ASSISTANT_EXPERIENCE.playground_kind,
  title: "Vanessa Core",
  panelAriaLabel: "Vanessa Core workspace",
  introText: "Work with Vanessa as a first-party assistant inside the shared AI workspace.",
  loadingText: "Loading Vanessa Core...",
  emptyStateText: "No messages yet. Start a Vanessa conversation to build the thread.",
  newSessionLabel: "New Vanessa session",
  emptySessionTitle: "Vanessa Core",
  draftPlaceholder: "Ask Vanessa anything",
  selectors: {
    model: true,
    knowledgeBase: false,
    assistant: false,
  },
  messaging: {
    mode: "stream",
    submitLabel: "Send to Vanessa",
    busyLabel: "Vanessa is responding...",
  },
  actions: {
    rename: true,
    delete: true,
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
