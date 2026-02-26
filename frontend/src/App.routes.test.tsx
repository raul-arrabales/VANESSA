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

vi.mock("./api/models", () => ({
  listModelCatalog: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  listModelAssignments: vi.fn(async () => [{ scope: "superadmin", model_ids: ["gpt-4"] }]),
  createModelCatalogItem: vi.fn(),
  updateModelAssignment: vi.fn(),
  listEnabledModels: vi.fn(async () => [{ id: "gpt-4", name: "GPT-4" }]),
  runInference: vi.fn(),
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
      <MemoryRouter initialEntries={["/welcome/superadmin/models"]}>
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
      <MemoryRouter initialEntries={["/welcome/superadmin/models"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Forbidden" })).toBeVisible();
  });
});
