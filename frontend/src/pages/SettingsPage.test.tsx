import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { AuthUser } from "../auth/types";
import SettingsPage from "./SettingsPage";

const modelApiMocks = vi.hoisted(() => ({
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
}));

let mockUser: AuthUser | null = null;

vi.mock("../api/models", () => ({
  listModelCatalog: vi.fn(async () => [
    { id: "gpt-4", name: "GPT-4" },
    { id: "mistral-small", name: "Mistral Small" },
  ]),
  listModelAssignments: vi.fn(async () => [
    { scope: "user", model_ids: ["mistral-small"] },
    { scope: "admin", model_ids: ["gpt-4"] },
  ]),
  listEnabledModels: vi.fn(async () => [{ id: "mistral-small", name: "Mistral Small" }]),
  createModelCatalogItem: modelApiMocks.createModelCatalogItem,
  updateModelAssignment: modelApiMocks.updateModelAssignment,
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: "token",
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

function renderSettings(initialPath = "/settings"): void {
  render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/settings" element={<SettingsPage />}>
            <Route path="design" element={<div>design-outlet</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: "user",
      is_active: true,
    };
  });

  it("shows user read-only model access and hides admin controls for standard users", async () => {
    renderSettings("/settings");

    expect(await screen.findByRole("heading", { name: "Model access" })).toBeVisible();
    expect(screen.getByText("Mistral Small")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "settings.admin.title" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add model to catalog" })).toBeNull();
  });

  it("shows assignment controls for admins", async () => {
    mockUser = {
      id: 3,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    renderSettings("/settings");

    expect(await screen.findByRole("heading", { name: "settings.admin.title" })).toBeVisible();
    const userScope = screen.getByLabelText("user model scope");
    expect(userScope).toBeVisible();
    expect(screen.queryByRole("button", { name: "Add model to catalog" })).toBeNull();
  });

  it("shows model catalog management for superadmin", async () => {
    mockUser = {
      id: 2,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    modelApiMocks.createModelCatalogItem.mockResolvedValueOnce({ id: "new-model", name: "New Model" });
    renderSettings("/settings");

    const addButton = await screen.findByRole("button", { name: "Add model to catalog" });
    expect(addButton).toBeVisible();

    await userEvent.type(screen.getByLabelText("Model name"), "New Model");
    await userEvent.click(addButton);

    expect(modelApiMocks.createModelCatalogItem).toHaveBeenCalledWith({ name: "New Model", provider: undefined }, "token");
  });

  it("renders nested outlet on /settings/design without overview cards", () => {
    renderSettings("/settings/design");

    expect(screen.getByText("design-outlet")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "settings.personalization.title" })).toBeNull();
    expect(screen.queryByLabelText("language.label")).toBeNull();
    expect(screen.queryByTestId("theme-toggle")).toBeNull();
  });
});
