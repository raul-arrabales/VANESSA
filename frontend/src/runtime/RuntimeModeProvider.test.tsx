import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../auth/authApi";
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
  const { mode, isLocked, source, isLoading, isSaving, error, setMode } = useRuntimeMode();

  return (
    <div>
      <p data-testid="mode">{mode ?? "none"}</p>
      <p data-testid="locked">{String(isLocked)}</p>
      <p data-testid="source">{source ?? "none"}</p>
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
    getRuntimeProfile.mockResolvedValue({ profile: "offline", locked: false, source: "database" });
    setRuntimeProfile.mockResolvedValue({ profile: "online", locked: false, source: "database" });
  });

  it("loads the runtime profile after auth", async () => {
    render(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => expect(getRuntimeProfile).toHaveBeenCalledWith("token"));
    expect(screen.getByTestId("mode")).toHaveTextContent("offline");
    expect(screen.getByTestId("locked")).toHaveTextContent("false");
    expect(screen.getByTestId("source")).toHaveTextContent("database");
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

  it("tracks lock metadata from the runtime profile API", async () => {
    getRuntimeProfile.mockResolvedValue({ profile: "offline", locked: true, source: "forced" });

    render(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("locked")).toHaveTextContent("true"));
    expect(screen.getByTestId("source")).toHaveTextContent("forced");
  });

  it("ignores late runtime profile failures after auth is cleared", async () => {
    let rejectRequest: ((reason?: unknown) => void) | undefined;
    getRuntimeProfile.mockImplementation(() => new Promise((_, reject) => {
      rejectRequest = reject;
    }));

    const { rerender } = render(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => expect(getRuntimeProfile).toHaveBeenCalledWith("token"));

    mockToken = "";
    mockIsAuthenticated = false;

    rerender(
      <RuntimeModeProvider>
        <RuntimeModeConsumer />
      </RuntimeModeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("mode")).toHaveTextContent("none");
      expect(screen.getByTestId("is-loading")).toHaveTextContent("false");
      expect(screen.getByTestId("error")).toHaveTextContent("");
    });

    rejectRequest?.(new ApiError("http://localhost:3000/", 500, "runtime_bootstrap_error"));

    await waitFor(() => {
      expect(screen.getByTestId("mode")).toHaveTextContent("none");
      expect(screen.getByTestId("is-loading")).toHaveTextContent("false");
      expect(screen.getByTestId("error")).toHaveTextContent("");
    });
  });
});
