import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AuthUser } from "./auth/types";
import App from "./App";

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
    setMode: vi.fn(),
  }),
}));
vi.mock("./api/models", () => ({
  listModelCatalog: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  listModelAssignments: vi.fn(async () => [{ scope: "superadmin", model_ids: ["gpt-4"] }]),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  listEnabledModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  runInference: vi.fn(),
  listModelCredentials: vi.fn(async () => []),
  createModelCredential: vi.fn(),
  revokeModelCredential: vi.fn(),
  registerManagedModel: vi.fn(),
  listAvailableManagedModels: vi.fn(async () => []),
}));

describe("App superadmin models route", () => {
  it("renders the page for superadmin", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    render(
      <MemoryRouter initialEntries={["/control/models"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "models.title" })).toBeVisible();
  });

  it("blocks non-superadmin users", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    render(
      <MemoryRouter initialEntries={["/control/system-health"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });

  it("falls through removed legacy routes to not-found", async () => {
    mockUser = {
      id: 2,
      email: "admin@example.com",
      username: "admin",
      role: "admin",
      is_active: true,
    };

    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeVisible();
  });

  it("always shows Home as the first breadcrumb link", async () => {
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };

    render(
      <MemoryRouter initialEntries={["/control/models"]}>
        <App />
      </MemoryRouter>,
    );

    const breadcrumbLinks = await screen.findAllByRole("link", { name: "nav.home" });
    expect(breadcrumbLinks[0]).toHaveAttribute("href", "/");
  });
});
