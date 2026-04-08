import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ThreadPanel from "./ThreadPanel";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import type { PlaygroundSessionViewModel } from "../types";

const clipboardMocks = vi.hoisted(() => ({
  writeText: vi.fn(),
}));

function buildSession(): PlaygroundSessionViewModel {
  return {
    id: "session-1",
    playgroundKind: "chat",
    title: "Session",
    titleSource: "auto",
    selectorState: {
      assistantRef: null,
      modelId: "safe-small",
      knowledgeBaseId: null,
    },
    messageCount: 2,
    createdAt: "2026-03-18T11:00:00Z",
    updatedAt: "2026-03-18T11:00:01Z",
    persistence: "saved",
    messages: [
      {
        id: "m-user",
        role: "user",
        content: "User question",
        metadata: {},
        createdAt: "2026-03-18T11:00:00Z",
      },
      {
        id: "m-assistant",
        role: "assistant",
        content: "Assistant answer",
        metadata: {
          sources: [
            {
              id: "doc-1",
              title: "Architecture Overview",
              text: "A longer retrieval-backed chunk that should be summarized when no snippet exists in the payload.",
              score: 0.92,
              score_kind: "similarity",
              relevance_kind: "similarity",
              metadata: { source_name: "Docs folder", ignored_empty: "" },
            },
          ],
        },
        createdAt: "2026-03-18T11:00:01Z",
      },
    ],
  };
}

describe("ThreadPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clipboardMocks.writeText.mockReset();
    clipboardMocks.writeText.mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: clipboardMocks.writeText,
      },
    });
  });

  it("shows a single assistant copy action and resets the copied state after a short delay", async () => {
    await renderWithAppProviders(
      <ThreadPanel
        activeSession={buildSession()}
        isBootstrapping={false}
        loadingText="Loading..."
        emptyStateText="Empty"
        threadRef={{ current: null }}
        handleScroll={() => undefined}
        hasUnreadContentBelow={false}
        isPinnedToBottom
        scrollToBottom={() => undefined}
        composer={<div />}
        composerHeight={96}
      />,
    );

    expect(screen.getAllByRole("button", { name: "Copy response" })).toHaveLength(1);
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText(/A longer retrieval-backed chunk/)).toBeVisible();
    expect(screen.queryByText(/Similarity/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy response" }));
      await Promise.resolve();
    });

    expect(clipboardMocks.writeText).toHaveBeenCalledWith("Assistant answer");
    expect(await screen.findByRole("button", { name: "Copied" })).toBeVisible();
    expect(screen.getAllByText("Copied").length).toBeGreaterThan(0);

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 2100));
    });

    expect(screen.getByRole("button", { name: "Copy response" })).toBeVisible();
  });
});
