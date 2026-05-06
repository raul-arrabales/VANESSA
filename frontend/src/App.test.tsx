import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import App from "./App";
import { renderWithAppProviders } from "./test/renderWithAppProviders";
import { t } from "./test/translation";

let mockUser: AuthUser | null = null;
const mockSetMode = vi.fn();
let mockRuntimeLocked = false;
let mockRuntimeError = "";
let mockRuntimeMode: "offline" | "online" = "offline";

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
    mode: mockRuntimeMode,
    isLocked: mockRuntimeLocked,
    source: mockRuntimeLocked ? "forced" : "database",
    isLoading: false,
    isSaving: false,
    error: mockRuntimeError,
    setMode: mockSetMode,
  }),
}));

describe("App header", () => {
  beforeEach(() => {
    mockUser = null;
    mockRuntimeLocked = false;
    mockRuntimeError = "";
    mockRuntimeMode = "offline";
    mockSetMode.mockReset();
    vi.restoreAllMocks();
  });

  async function renderApp(): Promise<HTMLElement> {
    const { container } = await renderWithAppProviders(<App />);
    return container;
  }

  it("renders icon-only user menu trigger with the display name as a tooltip", async () => {
    const container = await renderApp();

    const trigger = container.querySelector(".user-menu-trigger");
    expect(trigger).not.toBeNull();
    expect(container.querySelector(".app-topbar-brand-mark")).not.toBeNull();
    expect(container.querySelector(".user-menu-icon")).not.toBeNull();
    expect(container.querySelector(".user-menu-label")).toBeNull();
    expect(trigger).toHaveAttribute("title", await t("nav.guest"));
    expect(container.querySelector(".app-brand")).not.toBeNull();
    expect(container.querySelector(".welcome-page-brand-display")).not.toBeNull();
    expect(screen.getByRole("button", { name: await t("nav.guest") })).toBeVisible();
    expect(screen.getByRole("heading", { name: await t("app.title") })).toBeVisible();
    expect(screen.queryByText(await t("app.subtitle"))).toBeNull();
  });

  it("disables runtime toggle for non-superadmin users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderApp();

    expect(screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") })).toBeDisabled();
  });

  it("shows Vanessa AI in the primary nav for authenticated users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderApp();

    expect(screen.getByRole("link", { name: await t("nav.ai") })).toHaveAttribute("href", "/ai");
  });

  it("shows Control Panel in the user menu for authenticated users", async () => {
    mockUser = {
      id: 3,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    const user = userEvent.setup();

    await renderApp();
    await user.click(screen.getByRole("button", { name: "user" }));

    const userMenuPanel = document.querySelector(".user-menu-panel");
    expect(userMenuPanel).not.toBeNull();
    expect(within(userMenuPanel as HTMLElement).getByRole("link", { name: await t("nav.controlPanel") })).toHaveAttribute("href", "/control");
    expect(within(userMenuPanel as HTMLElement).getByRole("link", { name: "Docs" })).toHaveAttribute(
      "href",
      "https://raul-arrabales.github.io/VANESSA/",
    );
    expect(within(userMenuPanel as HTMLElement).getByRole("link", { name: "Docs" })).toHaveAttribute("target", "_blank");
  });

  it("enables the icon-only runtime mode button for superadmin users", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderApp();

    const runtimeButton = screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") });
    expect(runtimeButton).toBeEnabled();
    expect(runtimeButton).toHaveClass("runtime-mode-pill");
    expect(runtimeButton).toHaveAttribute("data-mode", "offline");
    expect(runtimeButton).toHaveAttribute(
      "title",
      await t("runtimeMode.switchTooltip", {
        mode: await t("runtimeMode.offline"),
        nextMode: await t("runtimeMode.online"),
      }),
    );
    expect(runtimeButton).not.toHaveTextContent(await t("runtimeMode.offline"));
  });

  it("shows online transfer indicator placeholders beside the online cloud icon", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    mockRuntimeMode = "online";

    const container = await renderApp();
    const runtimeButton = screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") });

    expect(runtimeButton).toHaveAttribute("data-mode", "online");
    expect(container.querySelector(".runtime-transfer-indicator[data-direction='upload']")).not.toBeNull();
    expect(container.querySelector(".runtime-transfer-indicator[data-direction='download']")).not.toBeNull();
  });

  it("disables runtime toggle when the runtime profile is environment-locked", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    mockRuntimeLocked = true;

    await renderApp();

    expect(screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") })).toBeDisabled();
    expect(screen.getByText(await t("runtimeMode.lockedByEnvironment", { mode: await t("runtimeMode.offline") }))).toBeVisible();
  });

  it("requires confirmation before changing runtime mode", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    const user = userEvent.setup();

    await renderApp();

    await user.click(screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") }));
    expect(screen.getByRole("dialog")).toBeVisible();
    await user.click(screen.getByRole("button", { name: await t("runtimeMode.dialog.cancel") }));

    expect(mockSetMode).not.toHaveBeenCalled();
  });

  it("changes runtime mode after confirming in the themed dialog", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    const user = userEvent.setup();

    await renderApp();

    await user.click(screen.getByRole("button", { name: await t("runtimeMode.toggleLabel") }));
    await user.click(screen.getByRole("button", { name: await t("runtimeMode.dialog.confirmOnline") }));

    expect(mockSetMode).toHaveBeenCalledWith("online");
  });

  it("does not show runtime load errors inline for guests", async () => {
    mockRuntimeError = "http://localhost:3000/";

    const container = await renderApp();
    const topbar = container.querySelector(".app-topbar");

    expect(screen.getByRole("button", { name: await t("nav.guest") })).toBeVisible();
    expect(topbar).not.toBeNull();
    expect(topbar).not.toHaveTextContent("http://localhost:3000/");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows authenticated runtime load errors in the action feedback modal instead of the header", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    mockRuntimeError = "http://localhost:3000/";

    const container = await renderApp();
    const topbar = container.querySelector(".app-topbar");

    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("http://localhost:3000/")).toBeVisible();
    expect(topbar).not.toBeNull();
    expect(topbar).not.toHaveTextContent("http://localhost:3000/");
  });
});
