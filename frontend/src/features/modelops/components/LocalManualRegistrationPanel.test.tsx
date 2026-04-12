import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LocalManualRegistrationPanel from "./LocalManualRegistrationPanel";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const modelApiMocks = vi.hoisted(() => ({
  registerManagedModel: vi.fn(),
}));

vi.mock("../../../api/modelops/models", () => ({
  registerManagedModel: modelApiMocks.registerManagedModel,
}));

describe("LocalManualRegistrationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelApiMocks.registerManagedModel.mockResolvedValue({ id: "phi-local" });
  });

  it("registers a manual local model, resets the form, and renders the test link", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalManualRegistrationPanel token="token" />, {
      route: "/control/models/local/register?view=manual",
    });

    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.type(screen.getByLabelText("Local path"), "/models/phi-local");
    await user.type(screen.getByLabelText("Comment"), "Ready for local tests");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(modelApiMocks.registerManagedModel).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "phi-local",
        name: "Phi Local",
        provider: "local",
        local_path: "/models/phi-local",
        task_key: "llm",
        category: "generative",
        comment: "Ready for local tests",
      }),
      "token",
    );
    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Test model" })).toHaveAttribute("href", "/control/models/phi-local/test");
    await waitFor(() => {
      expect(screen.getByLabelText("Model id")).toHaveValue("");
      expect(screen.getByLabelText("Model name")).toHaveValue("");
      expect(screen.getByLabelText("Local path")).toHaveValue("");
    });
  });

  it("keeps the form values and shows the shared error dialog when registration fails", async () => {
    modelApiMocks.registerManagedModel.mockRejectedValueOnce(new Error("Manual registration failed for phi-local"));
    const user = userEvent.setup();

    await renderWithAppProviders(<LocalManualRegistrationPanel token="token" />, {
      route: "/control/models/local/register?view=manual",
    });

    await user.type(screen.getByLabelText("Model id"), "phi-local");
    await user.type(screen.getByLabelText("Model name"), "Phi Local");
    await user.click(screen.getByRole("button", { name: "Register local model" }));

    expect(await screen.findByRole("dialog", { name: "Manual local registration" })).toBeVisible();
    expect(screen.getByText("Manual registration failed for phi-local")).toBeVisible();
    expect(screen.getByLabelText("Model id")).toHaveValue("phi-local");
    expect(screen.getByLabelText("Model name")).toHaveValue("Phi Local");
  });
});
