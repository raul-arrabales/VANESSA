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
            {
              id: "doc-2",
              title: "Architecture Overview",
              text: "Another chunk from the same file that must not appear as a repeated reference.",
              metadata: { source_path: "docs/architecture.md", page_number: 3 },
            },
          ],
          references: [
            {
              id: "ref-1",
              citation_label: "[1]",
              title: "Architecture Overview",
              description: "Docs folder",
              file_reference: "docs/architecture.md",
              file_url: "/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
              pages: [2, 3],
              source_ids: ["doc-1", "doc-2"],
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
    expect(screen.getByRole("button", { name: "References (1)" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Architecture Overview")).not.toBeInTheDocument();
    expect(screen.queryByText(/A longer retrieval-backed chunk/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Similarity/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "References (1)" }));
    });

    expect(screen.getByRole("button", { name: "References (1)" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Architecture Overview")).toBeVisible();
    expect(screen.getByText("Docs folder")).toBeVisible();
    expect(screen.getByText("docs/architecture.md")).toBeVisible();
    expect(screen.getByText("Pages 2, 3")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "/api/v1/playgrounds/knowledge-bases/kb-primary/documents/doc-1/source-file",
    );
    expect(screen.queryByText(/A longer retrieval-backed chunk/)).not.toBeInTheDocument();

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
