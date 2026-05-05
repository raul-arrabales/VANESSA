import type {
  PlaygroundSelectorState,
  PlaygroundSessionViewModel,
  PlaygroundWorkspaceConfig,
  PlaygroundWorkspaceOptions,
  PlaygroundMessageViewModel,
} from "./types";
import { hasSelector } from "./selectorConfig";

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
): PlaygroundMessageViewModel[] {
  return [
    ...previousMessages,
    {
      id: userMessageId,
      role: "user",
      content: prompt,
      metadata: {},
      createdAt: null,
    },
    {
      id: assistantMessageId,
      role: "assistant",
      content: "",
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
      ? { ...message, content: `${message.content}${text}` }
      : message
  ));
}

export function createDraftSession(
  config: PlaygroundWorkspaceConfig,
  options: PlaygroundWorkspaceOptions,
  source?: PlaygroundSessionViewModel | null,
): PlaygroundSessionViewModel {
  const selectorState: PlaygroundSelectorState = {
    assistantRef: source?.selectorState.assistantRef ?? options.defaultAssistantRef ?? config.defaultAssistantRef ?? null,
    modelId: source?.selectorState.modelId ?? options.models[0]?.id ?? null,
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
