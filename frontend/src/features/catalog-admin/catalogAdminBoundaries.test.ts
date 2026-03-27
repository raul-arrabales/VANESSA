import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import wrapperSource from "../../pages/CatalogControlPage.tsx?raw";

describe("catalog-admin boundaries", () => {
  it("routes point to the feature-owned catalog page", () => {
    expect(routesSource).toContain('../features/catalog-admin/pages/CatalogControlPage');
    expect(routesSource).not.toContain('../pages/CatalogControlPage');
  });

  it("the legacy catalog page is only a wrapper", () => {
    expect(wrapperSource.trim()).toBe('export { default } from "../features/catalog-admin/pages/CatalogControlPage";');
  });
});
