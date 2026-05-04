import { screen } from "@testing-library/react";
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
    expect(screen.getByRole("button", { name: "Configuración del chat" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Acciones de la conversación para Hilo uno" })).toBeVisible();
  });
});
