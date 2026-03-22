import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelOpsHomePage from "./ModelOpsHomePage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelOpsModels: vi.fn(),
  listModelCredentials: vi.fn(),
  listDownloadJobs: vi.fn(),
}));

let mockRole: "user" | "admin" | "superadmin" = "user";

vi.mock("../../../api/modelops", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
  listModelCredentials: modelApiMocks.listModelCredentials,
  listDownloadJobs: modelApiMocks.listDownloadJobs,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "tester", email: "t@example.com", role: mockRole, is_active: true },
    token: "token",
  }),
}));

describe("ModelOpsHomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelOpsModels.mockResolvedValue([
      { id: "gpt-4", name: "GPT-4", backend: "external_api", hosting: "cloud", owner_type: "platform", visibility_scope: "platform", lifecycle_state: "active", is_validation_current: true, last_validation_status: "success" },
      { id: "phi-local", name: "Phi Local", backend: "local", hosting: "local", owner_type: "user", visibility_scope: "private", lifecycle_state: "registered", is_validation_current: false, last_validation_status: null },
    ]);
    modelApiMocks.listModelCredentials.mockResolvedValue([{ id: "cred-1" }]);
    modelApiMocks.listDownloadJobs.mockResolvedValue([{ job_id: "job-1", status: "running" }]);
  });

  it("shows role-aware workflow cards for regular users", async () => {
    mockRole = "user";
    await renderWithAppProviders(<ModelOpsHomePage />);

    expect(await screen.findByRole("heading", { name: "ModelOps home" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Browse catalog" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Register cloud model" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Manage access" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Register local model" })).toBeNull();
  });

  it("shows superadmin-only entry cards", async () => {
    mockRole = "superadmin";
    await renderWithAppProviders(<ModelOpsHomePage />);

    expect(await screen.findByRole("link", { name: "Register local model" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Review local artifacts" })).toBeVisible();
    expect(screen.getByText("Active downloads")).toBeVisible();
  });
});
