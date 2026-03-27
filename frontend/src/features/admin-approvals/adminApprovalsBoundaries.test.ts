import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import authProviderSource from "../../auth/AuthProvider.tsx?raw";
import legacyPageSource from "../../pages/AdminApprovalsPage.tsx?raw";
import approvalsPageSource from "./pages/AdminApprovalsPage.tsx?raw";
import approvalsHookSource from "./hooks/useAdminApprovals.ts?raw";

describe("admin-approvals boundaries", () => {
  it("routes point to the feature-owned approvals page", () => {
    expect(routesSource).toContain('../features/admin-approvals/pages/AdminApprovalsPage');
    expect(routesSource).not.toContain('../pages/AdminApprovalsPage');
  });

  it("legacy page stays a thin wrapper", () => {
    expect(legacyPageSource).toContain('export { default } from "../features/admin-approvals/pages/AdminApprovalsPage"');
    expect(legacyPageSource).not.toContain("listPendingUsers");
    expect(legacyPageSource).not.toContain("activatePendingUser");
  });

  it("approvals flow is feature-owned instead of auth-context-owned", () => {
    expect(authProviderSource).not.toContain("activatePendingUser");
    expect(authProviderSource).not.toContain("listPendingUsers");
    expect(authProviderSource).not.toContain("updateUserRole");
    expect(approvalsPageSource).toContain("../hooks/useAdminApprovals");
    expect(approvalsHookSource).toContain("../api/adminApprovals");
  });
});
