import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelCatalogPage from "./ModelCatalogPage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelOpsModels: vi.fn(),
}));

vi.mock("../../../api/modelops/models", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: 1, username: "tester", email: "t@example.com", role: "user", is_active: true },
    token: "token",
    isAuthenticated: true,
  }),
}));

describe("ModelCatalogPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelOpsModels.mockResolvedValue([
      {
        id: "model-1",
        name: "Alpha",
        provider: "openai_compatible",
        backend: "external_api",
        hosting: "cloud",
        task_key: "llm",
        lifecycle_state: "active",
        is_validation_current: true,
        last_validation_status: "success",
      },
    ]);
  });

  it("renders inside the shared ModelOps workspace tabs", async () => {
    await renderWithAppProviders(<ModelCatalogPage />, { route: "/control/models/catalog" });

    expect(screen.getByRole("heading", { name: "ModelOps" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Model catalog" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { name: "Model catalog" })).toBeVisible();
    expect(await screen.findByText("Alpha")).toBeVisible();
  });
});
