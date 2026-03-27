import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../test/renderWithAppProviders";
import { t } from "../../test/translation";
import AdminApprovalsPage from "./pages/AdminApprovalsPage";

const approvalsApiMocks = vi.hoisted(() => ({
  listPendingUsers: vi.fn(),
  activatePendingUser: vi.fn(),
  promotePendingUser: vi.fn(),
}));

const feedbackMocks = vi.hoisted(() => ({
  showErrorFeedback: vi.fn(),
  showSuccessFeedback: vi.fn(),
}));

let mockUser = {
  id: 1,
  email: "root@example.com",
  username: "root",
  role: "superadmin" as const,
  is_active: true,
};

vi.mock("./api/adminApprovals", () => ({
  listPendingUsers: approvalsApiMocks.listPendingUsers,
  activatePendingUser: approvalsApiMocks.activatePendingUser,
  promotePendingUser: approvalsApiMocks.promotePendingUser,
}));

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mockUser,
    token: "token",
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
    register: vi.fn(),
  }),
}));

vi.mock("../../feedback/ActionFeedbackProvider", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../feedback/ActionFeedbackProvider")>();
  return {
    ...actual,
    useActionFeedback: () => ({
      showErrorFeedback: feedbackMocks.showErrorFeedback,
      showSuccessFeedback: feedbackMocks.showSuccessFeedback,
    }),
  };
});

describe("AdminApprovalsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = {
      id: 1,
      email: "root@example.com",
      username: "root",
      role: "superadmin",
      is_active: true,
    };
    approvalsApiMocks.listPendingUsers.mockResolvedValue([
      {
        id: 12,
        email: "pending@example.com",
        username: "pending",
        role: "user",
        is_active: false,
      },
    ]);
    approvalsApiMocks.activatePendingUser.mockResolvedValue({
      id: 12,
      email: "pending@example.com",
      username: "pending",
      role: "user",
      is_active: true,
    });
    approvalsApiMocks.promotePendingUser.mockResolvedValue({
      id: 12,
      email: "pending@example.com",
      username: "pending",
      role: "admin",
      is_active: false,
    });
  });

  it("loads pending users from the feature api", async () => {
    await renderWithAppProviders(<AdminApprovalsPage />);

    expect(await screen.findByRole("heading", { name: await t("auth.approvals.title") })).toBeVisible();

    await waitFor(() => {
      expect(approvalsApiMocks.listPendingUsers).toHaveBeenCalledWith("token");
    });
    expect(screen.getByText("#12 pending (pending@example.com)")).toBeVisible();
  });

  it("activates and promotes pending users", async () => {
    const user = userEvent.setup();

    await renderWithAppProviders(<AdminApprovalsPage />);
    await screen.findByText("#12 pending (pending@example.com)");

    await user.click(screen.getByRole("button", { name: await t("auth.approvals.submit") }));
    await waitFor(() => {
      expect(approvalsApiMocks.activatePendingUser).toHaveBeenCalledWith(12, "token");
    });

    await user.click(screen.getByRole("button", { name: await t("auth.approvals.promote") }));
    await waitFor(() => {
      expect(approvalsApiMocks.promotePendingUser).toHaveBeenCalledWith(12, "admin", "token");
    });
  });
});
