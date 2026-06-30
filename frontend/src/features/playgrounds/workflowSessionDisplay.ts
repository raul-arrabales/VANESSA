import type { PlaygroundSessionViewModel } from "./types";

export type PlaygroundWorkflowBadgeKind = "closed" | "loop";

export type PlaygroundWorkflowSessionDisplayState = {
  badgeKind: PlaygroundWorkflowBadgeKind | null;
  workflowCycle: number | null;
  isClosed: boolean;
};

export function getWorkflowSessionDisplayState(
  session: PlaygroundSessionViewModel | null | undefined,
): PlaygroundWorkflowSessionDisplayState {
  if (session?.workflowSessionState === "closed") {
    return {
      badgeKind: "closed",
      workflowCycle: session.workflowCycle ?? null,
      isClosed: true,
    };
  }
  if (session?.workflowExecutionMode === "loop" && session.workflowSessionState === "active") {
    return {
      badgeKind: "loop",
      workflowCycle: session.workflowCycle ?? null,
      isClosed: false,
    };
  }
  return {
    badgeKind: null,
    workflowCycle: session?.workflowCycle ?? null,
    isClosed: false,
  };
}
