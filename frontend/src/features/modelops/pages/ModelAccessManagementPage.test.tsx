import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelAccessManagementPage from "./ModelAccessManagementPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelOpsModels: vi.fn(),
}));

const accessApiMocks = vi.hoisted(() => ({
  listModelAssignments: vi.fn(),
  updateModelAssignment: vi.fn(),
}));

vi.mock("../../../api/modelops/models", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
}));

vi.mock("../../../api/modelops/access", () => ({
  listModelAssignments: accessApiMocks.listModelAssignments,
  updateModelAssignment: accessApiMocks.updateModelAssignment,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "admin", email: "admin@example.com", role: "admin", is_active: true },
    token: "token",
    isAuthenticated: true,
  }),
}));

describe("ModelAccessManagementPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelOpsModels.mockResolvedValue([
      {
        id: "model-1",
        name: "Test Model",
        provider: "openai_compatible",
        backend: "external_api",
        source: "external_provider",
        availability: "online_only",
        task_key: "llm",
        lifecycle_state: "active",
      },
    ]);
    accessApiMocks.listModelAssignments.mockResolvedValue([]);
    accessApiMocks.updateModelAssignment.mockResolvedValue({
      scope: "user",
      model_ids: ["model-1"],
    });
  });

  it("shows load failures in the shared feedback modal instead of inline errors", async () => {
    modelApiMocks.listModelOpsModels.mockRejectedValueOnce(new Error("Access data is unavailable."));
    const view = await renderWithAppProviders(<ModelAccessManagementPage />);

    expect(await screen.findByLabelText("Search")).toBeVisible();
    expect(await screen.findByRole("dialog", { name: "Model access management" })).toBeVisible();
    expect(screen.getAllByText("Access data is unavailable.")).toHaveLength(1);
    expect(view.container.querySelector(".error-text")).toBeNull();
  });

  it("shows assignment save success in the shared feedback modal with no inline success block", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<ModelAccessManagementPage />);

    expect(await screen.findByRole("heading", { name: "Model access management" })).toBeVisible();
    await user.click((await screen.findAllByRole("checkbox"))[0] as HTMLInputElement);

    expect(await screen.findByRole("dialog", { name: "Model access management" })).toBeVisible();
    expect(screen.getAllByText("Saved user assignments.")).toHaveLength(1);
    await waitFor(() => {
      expect(accessApiMocks.updateModelAssignment).toHaveBeenCalledWith("user", ["model-1"], "token");
    });
  });

  it("shows assignment save failures in the shared feedback modal instead of inline errors", async () => {
    accessApiMocks.updateModelAssignment.mockRejectedValueOnce(new Error("Assignment save failed."));
    const user = userEvent.setup();
    const view = await renderWithAppProviders(<ModelAccessManagementPage />);

    expect(await screen.findByRole("heading", { name: "Model access management" })).toBeVisible();
    await user.click((await screen.findAllByRole("checkbox"))[0] as HTMLInputElement);

    expect(await screen.findByRole("dialog", { name: "Model access management" })).toBeVisible();
    expect(screen.getAllByText("Assignment save failed.")).toHaveLength(1);
    expect(view.container.querySelector(".error-text")).toBeNull();
  });
});
