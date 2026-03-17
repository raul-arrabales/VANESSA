import { describe, expect, it } from "vitest";
import { appRoutes, removedLegacyPaths } from "./appRoutes";

describe("app route registry", () => {
  it("contains the canonical sitemap exactly once", () => {
    expect(appRoutes.map((route) => route.path)).toEqual([
      "/",
      "/login",
      "/register",
      "/settings",
      "/settings/design",
      "/control",
      "/control/approvals",
      "/control/quotes",
      "/control/system-health",
      "/control/platform",
      "/control/models",
      "/ai",
      "/ai/chat",
    ]);
  });

  it("does not expose removed legacy paths", () => {
    const currentPaths = new Set(appRoutes.map((route) => route.path));
    removedLegacyPaths.forEach((legacyPath) => {
      expect(currentPaths.has(legacyPath)).toBe(false);
    });
  });
});
