import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import AppChrome from "./features/app-shell/AppChrome";
import { renderWithAppProviders } from "./test/renderWithAppProviders";
import {
  findShellPathCue,
  findShellSidebar,
  findShellSidebarRegion,
  withinShellRegion,
} from "./test/shellQueries";
import { t } from "./test/translation";

let mockUser: AuthUser | null = null;

vi.mock("./auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: mockUser ? "token" : "",
    isAuthenticated: Boolean(mockUser),
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
  }),
}));

vi.mock("./runtime/RuntimeModeProvider", () => ({
  useRuntimeMode: () => ({
    mode: "offline",
    isLocked: false,
    source: "database",
    isLoading: false,
    isSaving: false,
    error: "",
    setMode: vi.fn(),
  }),
}));

vi.mock("./feedback/ActionFeedbackProvider", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./feedback/ActionFeedbackProvider")>();

  return {
    ...actual,
    useActionFeedback: () => ({
      showErrorFeedback: vi.fn(),
      showSuccessFeedback: vi.fn(),
    }),
  };
});

async function renderShell(route: string): Promise<void> {
  await renderWithAppProviders(
    <AppChrome>
      <section>
        <h1>Shell Content</h1>
      </section>
    </AppChrome>,
    { route },
  );
}

describe("AppChrome", () => {
  beforeEach(() => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    window.localStorage.clear();
  });

  it("renders the app shell with sidebar navigation and a minimal path cue", async () => {
    await renderShell("/control/models");

    const sidebar = await findShellSidebar(await t("nav.sidebar.aria"));
    expect(sidebar).toBeVisible();
    expect(screen.queryByRole("navigation", { name: await t("nav.breadcrumbs.aria") })).not.toBeInTheDocument();
    expect(withinShellRegion(sidebar).getByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute(
      "aria-current",
      "page",
    );

    const pathCue = await findShellPathCue(await t("nav.pathCue.aria"));
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.home") })).toHaveAttribute("href", "/");
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute(
      "href",
      "/control",
    );
    expect(withinShellRegion(pathCue).getByText(await t("nav.models"))).toBeVisible();
    expect(withinShellRegion(pathCue).queryByRole("link", { name: await t("nav.models") })).toBeNull();
  });

  it("renders concrete breadcrumb links for dynamic context routes in the top bar", async () => {
    const knowledgeBaseId = "45d38e20-f6fc-45bb-9e49-652a6c165bdd";

    await renderShell(`/control/context/${knowledgeBaseId}/sources`);

    const pathCue = await findShellPathCue(await t("nav.pathCue.aria"));
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.home") })).toHaveAttribute("href", "/");
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute(
      "href",
      "/control",
    );
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.context") })).toHaveAttribute(
      "href",
      "/control/context",
    );
    expect(withinShellRegion(pathCue).getByRole("link", { name: await t("nav.contextDetail") })).toHaveAttribute(
      "href",
      `/control/context/${knowledgeBaseId}`,
    );
    expect(withinShellRegion(pathCue).getByText(await t("nav.contextSources"))).toBeVisible();
    expect(withinShellRegion(pathCue).queryByRole("link", { name: await t("nav.contextSources") })).toBeNull();
  });

  it("persists sidebar collapse state and toggles the navigation drawer state", async () => {
    await renderShell("/control/models");

    const sidebar = await findShellSidebarRegion();
    expect(sidebar).toHaveAttribute("data-collapsed", "false");

    await userEvent.click(screen.getByRole("button", { name: await t("nav.sidebar.collapse") }));
    expect(sidebar).toHaveAttribute("data-collapsed", "true");
    expect(window.localStorage.getItem("vanessa.sidebar.collapsed")).toBe("true");

    await userEvent.click(screen.getByRole("button", { name: await t("nav.sidebar.open") }));
    expect(sidebar).toHaveAttribute("data-drawer-open", "true");

    await userEvent.click(screen.getByRole("button", { name: await t("nav.sidebar.close") }));
    expect(sidebar).toHaveAttribute("data-drawer-open", "false");
  });
});
