import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelOpsHomePage from "./ModelOpsHomePage";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  listModelOpsModels: vi.fn(),
  listModelCredentials: vi.fn(),
  listDownloadJobs: vi.fn(),
}));

vi.mock("../../../api/modelops/models", () => ({
  listModelOpsModels: modelApiMocks.listModelOpsModels,
}));

vi.mock("../../../api/modelops/credentials", () => ({
  listModelCredentials: modelApiMocks.listModelCredentials,
}));

vi.mock("../../../api/modelops/local", () => ({
  listDownloadJobs: modelApiMocks.listDownloadJobs,
}));

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    token: "token",
    user: {
      id: 1,
      username: "root",
      email: "root@example.com",
      role: "superadmin",
      is_active: true,
    },
  }),
}));

describe("ModelOpsHomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.listModelOpsModels.mockResolvedValue([
      {
        id: "local-1",
        name: "Local One",
        provider: "local",
        backend: "local",
        hosting: "local",
        owner_type: "user",
        visibility_scope: "private",
        lifecycle_state: "active",
        is_validation_current: true,
        last_validation_status: "success",
      },
      {
        id: "cloud-1",
        name: "Cloud One",
        provider: "openai_compatible",
        backend: "external_api",
        hosting: "cloud",
        owner_type: "platform",
        visibility_scope: "platform",
        lifecycle_state: "registered",
        is_validation_current: false,
        last_validation_status: null,
      },
    ]);
    modelApiMocks.listModelCredentials.mockResolvedValue([{ id: "cred-1" }]);
    modelApiMocks.listDownloadJobs.mockResolvedValue([
      { job_id: "job-1", status: "running" },
    ]);
  });

  it("renders translated summary card labels", async () => {
    await renderWithAppProviders(<ModelOpsHomePage />, { language: "es", route: "/control/models" });

    expect(screen.getByRole("link", { name: "Modelos" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Catalogo de modelos" })).toHaveAttribute("href", "/control/models/catalog");
    expect(screen.queryByRole("heading", { name: "Flujos" })).not.toBeInTheDocument();
    expect(await screen.findByText("Modelos totales")).toBeVisible();
    expect(screen.getByText("Modelos activos")).toBeVisible();
    expect(screen.getByText("Modelos locales")).toBeVisible();
    expect(screen.getByText("Descargas activas")).toBeVisible();
  });
});
