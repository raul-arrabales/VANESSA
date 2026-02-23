import { describe, expect, it } from "vitest";
import { getDefaultRouteForRole, hasRequiredRole } from "./roles";

describe("roles", () => {
  it("returns role-specific welcome routes", () => {
    expect(getDefaultRouteForRole("user")).toBe("/welcome/user");
    expect(getDefaultRouteForRole("admin")).toBe("/welcome/admin");
    expect(getDefaultRouteForRole("superadmin")).toBe("/welcome/superadmin");
  });

  it("keeps role hierarchy checks", () => {
    expect(hasRequiredRole("superadmin", "admin")).toBe(true);
    expect(hasRequiredRole("admin", "superadmin")).toBe(false);
  });
});
