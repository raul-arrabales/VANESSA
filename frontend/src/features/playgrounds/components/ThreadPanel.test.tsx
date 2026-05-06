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
        isSending={false}
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

  it("centers only the composer for a ready empty session", async () => {
    const emptySession = { ...buildSession(), messageCount: 0, messages: [] };

    const { container } = await renderWithAppProviders(
      <ThreadPanel
        activeSession={emptySession}
        isBootstrapping={false}
        isSending={false}
        loadingText="Loading..."
        emptyStateText="No messages yet"
        threadRef={{ current: null }}
        handleScroll={() => undefined}
        hasUnreadContentBelow={false}
        isPinnedToBottom
        scrollToBottom={() => undefined}
        composer={<button type="button">Send starter</button>}
        composerHeight={96}
      />,
    );

    expect(container.querySelector(".chatbot-thread-shell-starter")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Send starter" })).toBeVisible();
    expect(screen.queryByText("No messages yet")).not.toBeInTheDocument();
  });

  it("uses the threaded layout after an empty session has submitted", async () => {
    const emptySession = { ...buildSession(), messageCount: 0, messages: [] };

    const { container } = await renderWithAppProviders(
      <ThreadPanel
        activeSession={emptySession}
        isBootstrapping={false}
        isSending
        loadingText="Loading..."
        emptyStateText="No messages yet"
        threadRef={{ current: null }}
        handleScroll={() => undefined}
        hasUnreadContentBelow={false}
        isPinnedToBottom
        scrollToBottom={() => undefined}
        composer={<button type="button">Sending starter</button>}
        composerHeight={96}
      />,
    );

    expect(container.querySelector(".chatbot-thread-shell-starter")).toBeNull();
    expect(screen.getByText("No messages yet")).toBeVisible();
    expect(screen.getByRole("button", { name: "Sending starter" })).toBeVisible();
  });

  it("renders expandable assistant progress statuses with elapsed time", async () => {
    const session = {
      ...buildSession(),
      messages: [
        {
          id: "m-user",
          role: "user" as const,
          content: "User question",
          metadata: {},
          createdAt: "2026-03-18T11:00:00Z",
        },
        {
          id: "m-assistant",
          role: "assistant" as const,
          content: "",
          metadata: {
            statuses: [
              {
                id: "retrieval-1",
                kind: "retrieving",
                label: "Retrieved information from: docs",
                state: "completed",
                started_at: "2026-03-18T11:00:00Z",
                completed_at: "2026-03-18T11:00:01Z",
                duration_ms: 1234,
                summary: "2 results",
                details: {
                  query: "deployment profiles",
                  result_count: 2,
                },
              },
            ],
          },
          createdAt: "2026-03-18T11:00:01Z",
        },
      ],
    };

    await renderWithAppProviders(
      <ThreadPanel
        activeSession={session}
        isBootstrapping={false}
        isSending={false}
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

    const statusSummary = screen.getByText("Retrieved information from: docs - 1.2s").closest("summary");
    expect(statusSummary).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("deployment profiles")).not.toBeVisible();
    expect(screen.queryByRole("button", { name: "Copy response" })).toBeNull();

    await act(async () => {
      fireEvent.click(statusSummary as HTMLElement);
    });

    expect(statusSummary).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("deployment profiles")).toBeVisible();
    expect(screen.getByText("2 results")).toBeVisible();
  });
});
