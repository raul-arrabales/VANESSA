import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RuntimeModeProvider, useRuntimeMode } from "./RuntimeModeProvider";

const getRuntimeProfile = vi.fn();
const setRuntimeProfile = vi.fn();

let mockToken = "token";
let mockIsAuthenticated = true;

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    token: mockToken,
    isAuthenticated: mockIsAuthenticated,
  }),
}));

vi.mock("../api/runtime", () => ({
  getRuntimeProfile: (...args: unknown[]) => getRuntimeProfile(...args),
  setRuntimeProfile: (...args: unknown[]) => setRuntimeProfile(...args),
}));

function RuntimeModeConsumer(): JSX.Element {
  const { mode, isLoading, isSaving, error, setMode } = useRuntimeMode();

  return (
    <div>
      <p data-testid="mode">{mode ?? "none"}</p>
      <p data-testid="is-loading">{String(isLoading)}</p>
      <p data-testid="is-saving">{String(isSaving)}</p>
      <p data-testid="error">{error}</p>
      <button type="button" onClick={() => { void setMode("online").catch(() => undefined); }}>set-online</button>
    </div>
  );
}

describe("RuntimeModeProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockToken = "token";
    mockIsAuthenticated = true;
    getRuntimeProfile.mockResolvedValue({ profile: "offline" });
    setRuntimeProfile.mockResolvedValue({ profile: "online" });
  });

  it("loads the runtime profile after auth", async () => {
    render(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => expect(getRuntimeProfile).toHaveBeenCalledWith("token"));
    expect(screen.getByTestId("mode")).toHaveTextContent("offline");
  });

  it("optimistically updates and rolls back when update fails", async () => {
    const user = userEvent.setup();
    let rejectRequest: ((reason?: unknown) => void) | undefined;
    setRuntimeProfile.mockImplementation(() => new Promise((_, reject) => {
      rejectRequest = reject;
    }));

    render(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("mode")).toHaveTextContent("offline"));
    await user.click(screen.getByRole("button", { name: "set-online" }));

    await waitFor(() => expect(screen.getByTestId("mode")).toHaveTextContent("online"));

    if (rejectRequest) {
      rejectRequest(new Error("boom"));
    }
    await waitFor(() => expect(screen.getByTestId("mode")).toHaveTextContent("offline"));
  });
});
