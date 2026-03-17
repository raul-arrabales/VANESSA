import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import App from "./App";
import { renderWithAppProviders } from "./test/renderWithAppProviders";
import { t } from "./test/translation";

let mockUser: AuthUser | null = null;
const mockSetMode = vi.fn();

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
    activatePendingUser: vi.fn(),
    listPendingUsers: vi.fn(),
    updateUserRole: vi.fn(),
  }),
}));

vi.mock("./runtime/RuntimeModeProvider", () => ({
  useRuntimeMode: () => ({
    mode: "offline",
    isLoading: false,
    isSaving: false,
    error: "",
    setMode: mockSetMode,
  }),
}));

describe("App header", () => {
  beforeEach(() => {
    mockUser = null;
    mockSetMode.mockReset();
    vi.restoreAllMocks();
  });

  async function renderApp(): Promise<HTMLElement> {
    const { container } = await renderWithAppProviders(<App />);
    return container;
  }

  it("renders user icon and label in the menu trigger", async () => {
    const container = await renderApp();

    const trigger = container.querySelector(".user-menu-trigger");
    expect(trigger).not.toBeNull();
    expect(container.querySelector(".user-menu-icon")).not.toBeNull();
    expect(container.querySelector(".user-menu-label")).not.toBeNull();
    expect(screen.getByRole("button", { name: await t("nav.guest") })).toBeVisible();
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

    expect(screen.getByRole("switch", { name: await t("runtimeMode.toggleLabel") })).toBeDisabled();
  });

  it("enables runtime toggle for superadmin users", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderApp();

    expect(screen.getByRole("switch", { name: await t("runtimeMode.toggleLabel") })).toBeEnabled();
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

    await user.click(screen.getByRole("switch", { name: await t("runtimeMode.toggleLabel") }));
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

    await user.click(screen.getByRole("switch", { name: await t("runtimeMode.toggleLabel") }));
    await user.click(screen.getByRole("button", { name: await t("runtimeMode.dialog.confirmOnline") }));

    expect(mockSetMode).toHaveBeenCalledWith("online");
  });
});
