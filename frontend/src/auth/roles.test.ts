import { describe, expect, it } from "vitest";
import { getDefaultRouteForRole, hasRequiredRole } from "./roles";

describe("roles", () => {
  it("returns the welcome home route for every role", () => {
    expect(getDefaultRouteForRole("user")).toBe("/");
    expect(getDefaultRouteForRole("admin")).toBe("/");
    expect(getDefaultRouteForRole("superadmin")).toBe("/");
  });

  it("keeps hierarchy checks unchanged", () => {
    expect(hasRequiredRole("superadmin", "admin")).toBe(true);
    expect(hasRequiredRole("admin", "user")).toBe(true);
    expect(hasRequiredRole("user", "admin")).toBe(false);
  });
});
