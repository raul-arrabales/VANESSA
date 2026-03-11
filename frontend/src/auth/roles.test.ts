import { describe, expect, it } from "vitest";
import { getDefaultRouteForRole, hasRequiredRole } from "./roles";

describe("roles", () => {
  it("returns the canonical control route for every role", () => {
    expect(getDefaultRouteForRole("user")).toBe("/control");
    expect(getDefaultRouteForRole("admin")).toBe("/control");
    expect(getDefaultRouteForRole("superadmin")).toBe("/control");
  });

  it("keeps hierarchy checks unchanged", () => {
    expect(hasRequiredRole("superadmin", "admin")).toBe(true);
    expect(hasRequiredRole("admin", "user")).toBe(true);
    expect(hasRequiredRole("user", "admin")).toBe(false);
  });
});
