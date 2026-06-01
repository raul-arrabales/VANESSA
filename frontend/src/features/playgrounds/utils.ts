import type {
  PlaygroundSelectorState,
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
  PlaygroundMessageViewModel,
  PlaygroundRunStatus,
} from "./types";
import type { PlaygroundMessageContentPart } from "../../api/playgrounds";
import { hasSelector } from "./selectorConfig";
import { messageText, textContentPart } from "./messageContent";

export function sortSessions(sessions: PlaygroundSessionViewModel[]): PlaygroundSessionViewModel[] {
  return [...sessions].sort((left, right) => {
    const leftTime = left.updatedAt ? Date.parse(left.updatedAt) : 0;
    const rightTime = right.updatedAt ? Date.parse(right.updatedAt) : 0;
    return rightTime - leftTime;
  });
}

export function upsertSession(
  sessions: PlaygroundSessionViewModel[],
  nextSession: PlaygroundSessionViewModel,
): PlaygroundSessionViewModel[] {
  const filtered = sessions.filter((session) => session.id !== nextSession.id);
  return sortSessions([nextSession, ...filtered]);
}

export function removeSession(
  sessions: PlaygroundSessionViewModel[],
  sessionId: string,
): PlaygroundSessionViewModel[] {
  return sessions.filter((session) => session.id !== sessionId);
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Date(value).toLocaleString();
}

export function createTransientMessageId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createOptimisticMessages(
  previousMessages: PlaygroundMessageViewModel[],
  prompt: string,
  userMessageId: string,
  assistantMessageId: string,
  contentParts: PlaygroundMessageContentPart[] = prompt ? [textContentPart(prompt)] : [],
): PlaygroundMessageViewModel[] {
  const userContent = prompt || messageText({ content: "", content_parts: contentParts, metadata: {} });
  return [
    ...previousMessages,
    {
      id: userMessageId,
      role: "user",
      content: userContent,
      content_parts: contentParts,
      metadata: { content_parts: contentParts },
      createdAt: null,
    },
    {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      content_parts: [],
      metadata: { transient: true },
      createdAt: null,
      isTransient: true,
    },
  ];
}

export function updateTransientAssistantMessage(
  messages: PlaygroundMessageViewModel[],
  assistantMessageId: string,
  text: string,
): PlaygroundMessageViewModel[] {
  return messages.map((message) => (
    message.id === assistantMessageId
      ? { ...message, content: `${message.content}${text}`, content_parts: [textContentPart(`${message.content}${text}`)] }
      : message
  ));
}

export function updateTransientAssistantStatus(
  messages: PlaygroundMessageViewModel[],
  assistantMessageId: string,
  status: PlaygroundRunStatus,
): PlaygroundMessageViewModel[] {
  return messages.map((message) => {
    if (message.id !== assistantMessageId) {
      return message;
    }
    const currentStatuses = Array.isArray(message.metadata.statuses) ? message.metadata.statuses : [];
    const nextStatuses = [
      ...currentStatuses.filter((item) => (
        item.id !== status.id
        && !(status.kind === "thinking" && item.kind === "thinking" && item.id.endsWith("-thinking") && item.state === "running")
      )),
      status,
    ];
    return {
      ...message,
      metadata: {
        ...message.metadata,
        statuses: nextStatuses,
      },
    };
  });
}

export function resolveAvailableModelId(
  requestedModelId: string | null | undefined,
  models: PlaygroundWorkspaceOptions["models"],
): string | null {
  const fallbackModelId = models[0]?.id ?? null;
  if (!requestedModelId) {
    return fallbackModelId;
  }
  return models.some((model) => model.id === requestedModelId) ? requestedModelId : fallbackModelId;
}

export function createDraftSession(
  config: PlaygroundWorkspaceConfig,
  options: PlaygroundWorkspaceOptions,
  source?: PlaygroundSessionViewModel | null,
): PlaygroundSessionViewModel {
  const selectorState: PlaygroundSelectorState = {
    assistantRef: source?.selectorState.assistantRef ?? options.defaultAssistantRef ?? config.defaultAssistantRef ?? null,
    modelId: resolveAvailableModelId(source?.selectorState.modelId, options.models),
    knowledgeBaseId: hasSelector(config, "knowledgeBase")
      ? (source?.selectorState.knowledgeBaseId ?? options.defaultKnowledgeBaseId ?? null)
      : null,
  };

  return {
    id: createTransientMessageId(`draft-${config.playgroundKind}`),
    playgroundKind: config.playgroundKind,
    title: config.emptySessionTitle,
    titleSource: "auto",
    selectorState,
    messageCount: 0,
    createdAt: null,
    updatedAt: null,
    messages: [],
    persistence: "draft",
  };
}

export function createTemporarySession(
  config: PlaygroundWorkspaceConfig,
  options: PlaygroundWorkspaceOptions,
  source?: PlaygroundSessionViewModel | null,
): PlaygroundSessionViewModel {
  return {
    ...createDraftSession(config, options, source),
    id: createTransientMessageId(`temporary-${config.playgroundKind}`),
    title: config.temporarySessionTitle,
    persistence: "temporary",
  };
}
