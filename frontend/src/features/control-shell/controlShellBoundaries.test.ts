import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import controlPageSource from "../../pages/ControlPage.tsx?raw";
import controlShellPageSource from "./pages/ControlShellPage.tsx?raw";
import controlItemsSource from "./controlItems.ts?raw";

describe("control-shell boundaries", () => {
  it("routes point to the feature-owned control shell page", () => {
    expect(routesSource).toContain('../features/control-shell/pages/ControlShellPage');
    expect(routesSource).not.toContain('../pages/ControlPage');
  });

  it("legacy control page stays a thin wrapper", () => {
    expect(controlPageSource).toContain('export { default } from "../features/control-shell/pages/ControlShellPage"');
    expect(controlPageSource).not.toContain("OptionCardGrid");
    expect(controlPageSource).not.toContain("useTranslation");
  });

  it("control card ownership lives in the feature config", () => {
    expect(controlItemsSource).toContain('to: "/control/approvals"');
    expect(controlItemsSource).toContain('to: "/control/quotes"');
    expect(controlShellPageSource).toContain('../controlItems');
  });
});
