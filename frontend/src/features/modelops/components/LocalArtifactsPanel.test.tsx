import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LocalArtifactsPanel from "./LocalArtifactsPanel";
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

const readyArtifact = {
  artifact_id: "artifact-1",
  suggested_model_id: "phi-local",
  name: "Phi Local",
  storage_path: "/models/phi-local",
  task_key: "llm",
  artifact_status: "ready",
  lifecycle_state: "downloaded",
  validation_hint: "ready",
  ready_for_registration: true,
};

describe("LocalArtifactsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localApiMocks.listLocalModelArtifacts.mockResolvedValue([readyArtifact]);
    modelApiMocks.registerExistingManagedModel.mockResolvedValue({ id: "phi-local" });
  });

  it("renders the loading state before artifacts resolve", async () => {
    let resolveArtifacts: (value: unknown) => void = () => {};
    localApiMocks.listLocalModelArtifacts.mockReturnValueOnce(new Promise((resolve) => {
      resolveArtifacts = resolve;
    }));

    await renderWithAppProviders(<LocalArtifactsPanel token="token" />, {
      route: "/control/models/local/register?view=artifacts",
    });

    expect(screen.getByText("Loading ModelOps data...")).toBeVisible();
    resolveArtifacts([]);
    expect(await screen.findByText("No local artifacts are available yet.")).toBeVisible();
  });

  it("renders the empty state when no local artifacts are available", async () => {
    localApiMocks.listLocalModelArtifacts.mockResolvedValueOnce([]);

    await renderWithAppProviders(<LocalArtifactsPanel token="token" />, {
      route: "/control/models/local/register?view=artifacts",
    });

    expect(await screen.findByText("No local artifacts are available yet.")).toBeVisible();
  });

  it("registers a ready artifact and refreshes the local artifact list", async () => {
    localApiMocks.listLocalModelArtifacts
      .mockResolvedValueOnce([readyArtifact])
      .mockResolvedValueOnce([
        {
          ...readyArtifact,
          linked_model_id: "phi-local",
          ready_for_registration: false,
        },
      ]);
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalArtifactsPanel token="token" />, {
      route: "/control/models/local/register?view=artifacts",
    });

    expect(await screen.findByText("Phi Local")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(modelApiMocks.registerExistingManagedModel).toHaveBeenCalledWith("phi-local", "token");
    expect(await screen.findByText("Artifact registered successfully.")).toBeVisible();
    await waitFor(() => {
      expect(localApiMocks.listLocalModelArtifacts).toHaveBeenCalledTimes(2);
    });
  });

  it("shows a local error message when artifact registration fails", async () => {
    modelApiMocks.registerExistingManagedModel.mockRejectedValueOnce(new Error("Artifact cannot be registered"));
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalArtifactsPanel token="token" />, {
      route: "/control/models/local/register?view=artifacts",
    });

    expect(await screen.findByText("Phi Local")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByText("Artifact cannot be registered")).toBeVisible();
  });
});
