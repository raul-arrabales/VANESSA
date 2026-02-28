import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RuntimeProfileSection from "./RuntimeProfileSection";

const fetchRuntimeProfile = vi.fn();
const updateRuntimeProfile = vi.fn();

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
    token: "token",
  }),
}));

vi.mock("../auth/authApi", () => ({
  ApiError: class extends Error {},
  fetchRuntimeProfile: (...args: unknown[]) => fetchRuntimeProfile(...args),
  updateRuntimeProfile: (...args: unknown[]) => updateRuntimeProfile(...args),
}));

describe("RuntimeProfileSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchRuntimeProfile.mockResolvedValue({ profile: "offline" });
    updateRuntimeProfile.mockResolvedValue({ profile: "online" });
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

    await waitFor(() => expect(fetchRuntimeProfile).toHaveBeenCalledWith("token"));
    fireEvent.click(screen.getByRole("radio", { name: "settings.runtime.options.online" }));

    await waitFor(() => expect(updateRuntimeProfile).toHaveBeenCalledWith("online", "token"));
  });
});
