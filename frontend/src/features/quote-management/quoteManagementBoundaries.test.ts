import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import legacyPageSource from "../../pages/QuoteManagementPage.tsx?raw";
import featurePageSource from "./pages/QuoteManagementPage.tsx?raw";
import featureHookSource from "./hooks/useQuoteManagement.ts?raw";

describe("quote-management boundaries", () => {
  it("routes point to the feature-owned quote page", () => {
    expect(routesSource).toContain('../features/quote-management/pages/QuoteManagementPage');
    expect(routesSource).not.toContain('../pages/QuoteManagementPage');
  });

  it("legacy page stays a thin wrapper", () => {
    expect(legacyPageSource).toContain('export { default } from "../features/quote-management/pages/QuoteManagementPage"');
    expect(legacyPageSource).not.toContain("QuoteManagementEditorModal");
    expect(legacyPageSource).not.toContain("useQuoteManagement");
  });

  it("feature-owned quote page resolves through the feature hook", () => {
    expect(featurePageSource).toContain('../hooks/useQuoteManagement');
    expect(featureHookSource).toContain('../../../api/quoteAdmin');
    expect(featureHookSource).not.toContain('../../../hooks/useQuoteManagement');
  });
});
