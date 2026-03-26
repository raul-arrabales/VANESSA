import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../test/renderWithAppProviders";
import { t } from "../test/translation";
import type { AuthUser } from "../auth/types";
import ControlPage from "./ControlPage";

let mockUser: AuthUser | null = null;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

async function renderPage(): Promise<void> {
  await renderWithAppProviders(<ControlPage />);
}

describe("ControlPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("hides the quotes control from regular users", async () => {
    mockUser = {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };

    await renderPage();

    expect(screen.queryByRole("link", { name: await t("control.items.profile.title") })).toBeNull();
    expect(screen.queryByRole("link", { name: await t("control.items.quotes.title") })).toBeNull();
    expect(screen.getByRole("link", { name: await t("control.items.models.title") })).toHaveAttribute("href", "/control/models");
  });

  it("shows the quotes control for admin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    await renderPage();

    expect(screen.queryByRole("link", { name: await t("control.items.profile.title") })).toBeNull();
    expect(screen.getByRole("link", { name: await t("control.items.quotes.title") })).toHaveAttribute("href", "/control/quotes");
    expect(screen.getByRole("link", { name: await t("control.items.context.title") })).toHaveAttribute("href", "/control/context");
    expect(screen.queryByRole("link", { name: await t("control.items.platform.title") })).toBeNull();
  });

  it("shows the platform control only for superadmin users", async () => {
    mockUser = {
      id: 3,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    await renderPage();

    expect(screen.queryByRole("link", { name: await t("control.items.profile.title") })).toBeNull();
    expect(screen.getByRole("link", { name: await t("control.items.platform.title") })).toHaveAttribute("href", "/control/platform");
    expect(screen.getByRole("link", { name: await t("control.items.catalog.title") })).toHaveAttribute("href", "/control/catalog");
  });
});
