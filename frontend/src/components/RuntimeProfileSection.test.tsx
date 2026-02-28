import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RuntimeProfileSection from "./RuntimeProfileSection";

const setMode = vi.fn();

let mockRole: "user" | "superadmin" = "user";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "user@example.com",
      username: "user",
      role: mockRole,
      is_active: true,
    },
  }),
}));

vi.mock("../runtime/RuntimeModeProvider", () => ({
  useRuntimeMode: () => ({
    mode: "offline",
    isLoading: false,
    isSaving: false,
    error: "",
    setMode,
  }),
}));

describe("RuntimeProfileSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setMode.mockResolvedValue("online");
    mockRole = "user";
  });

  it("shows restriction message for non-superadmin users", async () => {
    render(<RuntimeProfileSection />);

    await screen.findByText("settings.runtime.restrictionMessage");
    expect(screen.getByRole("group")).toBeDisabled();
  });

  it("allows superadmin users to change runtime profile", async () => {
    mockRole = "superadmin";
    render(<RuntimeProfileSection />);

    fireEvent.click(screen.getByRole("radio", { name: "settings.runtime.options.online" }));

    await waitFor(() => expect(setMode).toHaveBeenCalledWith("online"));
  });
});
