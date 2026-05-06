import type {
  PlaygroundAssistantOption,
  PlaygroundKnowledgeBaseOption,
  PlaygroundKind,
  PlaygroundMessage,
  PlaygroundRunStatus,
  PlaygroundSessionDetail,
  PlaygroundSessionSummary,
} from "../../api/playgrounds";

export type PlaygroundVariant = PlaygroundKind;

export type PlaygroundSelectorState = {
  assistantRef: string | null;
  modelId: string | null;
  knowledgeBaseId: string | null;
};

export type PlaygroundMessageViewModel = PlaygroundMessage & {
  isTransient?: boolean;
};

export type { PlaygroundRunStatus };

export type PlaygroundSessionPersistence = "draft" | "saved" | "temporary";

export type PlaygroundSessionViewModel = {
  id: string;
  playgroundKind: PlaygroundVariant;
  title: string;
  titleSource: "auto" | "manual";
  selectorState: PlaygroundSelectorState;
  messageCount: number;
  createdAt: string | null;
  updatedAt: string | null;
  messages: PlaygroundMessageViewModel[];
  persistence: PlaygroundSessionPersistence;
};

export type PlaygroundSelectorKind = "assistant" | "knowledgeBase" | "model";

export type PlaygroundWorkspaceConfig = {
  playgroundKind: PlaygroundVariant;
  title: string;
  panelAriaLabel: string;
  introText: string;
  loadingText: string;
  modelLoadingText: string;
  knowledgeBaseLoadingText: string;
  emptyStateText: string;
  newSessionLabel: string;
  emptySessionTitle: string;
  temporarySessionLabel: string;
  temporarySessionTitle: string;
  draftPlaceholder: string;
  inlineSelectors: PlaygroundSelectorKind[];
  settingsSelectors: PlaygroundSelectorKind[];
  messaging: {
    mode: "stream" | "request";
    submitLabel: string;
    busyLabel: string;
    stopLabel: string;
  };
  actions: {
    rename: boolean;
    delete: boolean;
  };
  sessionBootstrap: {
    mode: "saved-first" | "draft-first";
    historyLoadingText: string;
  };
  prompts: {
    rename: string;
    deleteConfirm: string;
  };
  feedback: {
    createError: string;
    updateModelError: string;
    updateKnowledgeBaseError: string;
    updateAssistantError: string;
    renameError: string;
    deleteError: string;
    sendError: string;
    optionsError: string;
    sessionsError: string;
    sessionError: string;
    missingModel: string;
    missingKnowledgeBase: string;
  };
  defaultAssistantRef?: string | null;
};

export type PlaygroundWorkspaceOptions = {
  models: Array<{
    id: string;
    displayName: string;
  }>;
  assistants: PlaygroundAssistantOption[];
  knowledgeBases: PlaygroundKnowledgeBaseOption[];
  defaultAssistantRef: string | null;
  defaultKnowledgeBaseId: string | null;
  configurationMessage: string;
};

export function mapPlaygroundSessionSummary(
  session: PlaygroundSessionSummary,
): PlaygroundSessionViewModel {
  return {
    id: session.id,
    playgroundKind: session.playground_kind,
    title: session.title,
    titleSource: session.title_source,
    selectorState: {
      assistantRef: session.assistant_ref,
      modelId: session.model_selection.model_id,
      knowledgeBaseId: session.knowledge_binding.knowledge_base_id,
    },
    messageCount: session.message_count,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
    messages: [],
    persistence: "saved",
  };
}

export function mapPlaygroundSessionDetail(
  session: PlaygroundSessionDetail,
): PlaygroundSessionViewModel {
  return {
    ...mapPlaygroundSessionSummary(session),
    messages: session.messages.map((message) => ({ ...message })),
  };
}
