import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LocalArtifactsPage from "./LocalArtifactsPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const localApiMocks = vi.hoisted(() => ({
  listLocalModelArtifacts: vi.fn(),
}));

const modelApiMocks = vi.hoisted(() => ({
  registerExistingManagedModel: vi.fn(),
}));

vi.mock("../../../api/modelops/local", () => ({
  listLocalModelArtifacts: localApiMocks.listLocalModelArtifacts,
}));

vi.mock("../../../api/modelops/models", () => ({
  registerExistingManagedModel: modelApiMocks.registerExistingManagedModel,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "superadmin", email: "sa@example.com", role: "superadmin", is_active: true },
    token: "token",
    isAuthenticated: true,
  }),
}));

describe("LocalArtifactsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localApiMocks.listLocalModelArtifacts.mockResolvedValue([
      {
        artifact_id: "artifact-1",
        suggested_model_id: "phi-local",
        name: "Phi Local",
        storage_path: "/models/phi-local",
        task_key: "llm",
        artifact_status: "ready",
        lifecycle_state: "downloaded",
        validation_hint: "ready",
        ready_for_registration: true,
      },
    ]);
    modelApiMocks.registerExistingManagedModel.mockResolvedValue({ id: "phi-local" });
  });

  it("renders inside the shared ModelOps workspace tabs", async () => {
    await renderWithAppProviders(<LocalArtifactsPage />, { route: "/control/models/local/artifacts" });

    expect(screen.getByRole("heading", { name: "ModelOps" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Local artifacts" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { name: "Local artifacts" })).toBeVisible();
    expect(await screen.findByText("Phi Local")).toBeVisible();
  });
});
