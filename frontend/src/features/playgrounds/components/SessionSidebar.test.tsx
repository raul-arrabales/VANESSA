import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SessionSidebar from "./SessionSidebar";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

describe("SessionSidebar", () => {
  it("localizes sidebar aria and action labels", async () => {
    await renderWithAppProviders(
      <SessionSidebar
        title="Conversaciones"
        introText="Texto"
        historyLoadingText="Cargando"
        newSessionLabel="Nuevo chat"
        temporarySessionLabel="Chat temporal"
        settingsLabel="Configuración del chat"
        showSettings
        isSearchOpen={false}
        searchFilters={{}}
        isSearchActive={false}
        sessions={[
          {
            id: "session-1",
            playgroundKind: "chat",
            title: "Hilo uno",
            titleSource: "manual",
            selectorState: {
              assistantRef: null,
              modelId: "safe-small",
              knowledgeBaseId: null,
            },
            messageCount: 1,
            createdAt: "2026-03-18T11:00:00Z",
            updatedAt: "2026-03-18T11:00:00Z",
            messages: [],
            persistence: "saved",
          },
        ]}
        activeSessionId="session-1"
        canCreateSession
        isInteractionLocked={false}
        isCollapsed={false}
        isHistoryLoading={false}
        historyError=""
        onToggleCollapsed={vi.fn()}
        onCreateSession={vi.fn()}
        onCreateTemporarySession={vi.fn()}
        onOpenSettings={vi.fn()}
        onToggleSearch={vi.fn()}
        onSearchFiltersChange={vi.fn()}
        onClearSearch={vi.fn()}
        onSelectSession={vi.fn()}
        onRenameSession={vi.fn()}
        onDeleteSession={vi.fn()}
        canRenameSession
        canDeleteSession
      />,
      { language: "es" },
    );

    expect(screen.getByRole("complementary", { name: "Historial de conversaciones" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Contraer historial de conversaciones" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Nuevo chat" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Buscar conversaciones" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Chat temporal" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Configuración del chat" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Acciones de la conversación para Hilo uno" })).toBeVisible();
  });

  it("renders inline search controls and the filtered empty state", async () => {
    const onSearchFiltersChange = vi.fn();
    const onClearSearch = vi.fn();

    await renderWithAppProviders(
      <SessionSidebar
        title="Chat"
        introText=""
        historyLoadingText="Loading"
        newSessionLabel="New chat"
        temporarySessionLabel="Temporary chat"
        settingsLabel="Chat settings"
        showSettings
        isSearchOpen
        searchFilters={{ titleQuery: "old", updatedFrom: "2026-03-01", updatedTo: "2026-03-18" }}
        isSearchActive
        sessions={[]}
        activeSessionId={null}
        canCreateSession
        isInteractionLocked={false}
        isCollapsed={false}
        isHistoryLoading={false}
        historyError=""
        onToggleCollapsed={vi.fn()}
        onCreateSession={vi.fn()}
        onCreateTemporarySession={vi.fn()}
        onOpenSettings={vi.fn()}
        onToggleSearch={vi.fn()}
        onSearchFiltersChange={onSearchFiltersChange}
        onClearSearch={onClearSearch}
        onSelectSession={vi.fn()}
        onRenameSession={vi.fn()}
        onDeleteSession={vi.fn()}
        canRenameSession
        canDeleteSession
      />,
    );

    expect(screen.getByRole("search", { name: "Search conversation history" })).toBeVisible();
    expect(screen.getByLabelText("Title")).toHaveValue("old");
    expect(screen.getByLabelText("Updated from")).toHaveValue("2026-03-01");
    expect(screen.getByLabelText("Updated to")).toHaveValue("2026-03-18");
    expect(screen.getByText("No conversations match these filters.")).toBeVisible();

    await userEvent.clear(screen.getByLabelText("Title"));
    expect(onSearchFiltersChange).toHaveBeenLastCalledWith({
      titleQuery: "",
      updatedFrom: "2026-03-01",
      updatedTo: "2026-03-18",
    });

    await userEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(onClearSearch).toHaveBeenCalled();
  });
});
