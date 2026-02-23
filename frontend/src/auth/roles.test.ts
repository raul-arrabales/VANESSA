import { describe, expect, it } from "vitest";
import { getDefaultRouteForRole, hasRequiredRole } from "./roles";

describe("roles", () => {
  it("returns a role-specific welcome route", () => {
    expect(getDefaultRouteForRole("user")).toBe("/welcome/user");
    expect(getDefaultRouteForRole("admin")).toBe("/welcome/admin");
    expect(getDefaultRouteForRole("superadmin")).toBe("/welcome/superadmin");
  });

  it("keeps hierarchy checks unchanged", () => {
    expect(hasRequiredRole("superadmin", "admin")).toBe(true);
    expect(hasRequiredRole("admin", "user")).toBe(true);
    expect(hasRequiredRole("user", "admin")).toBe(false);
  });
});
