import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import indexSource from "./index.ts?raw";
import pageSource from "./pages/VanessaCorePage.tsx?raw";
import configSource from "./vanessaCoreConfig.ts?raw";

describe("vanessa-core boundaries", () => {
  it("routes point to the feature-owned Vanessa page", () => {
    expect(routesSource).toContain('../features/vanessa-core/pages/VanessaCorePage');
    expect(routesSource).toContain('path: "/ai/vanessa"');
  });

  it("feature ownership no longer stays placeholder-only", () => {
    expect(indexSource).toContain("vanessaCoreFeatureReady = true");
    expect(indexSource).not.toContain("vanessaCoreFeatureReady = false");
  });

  it("Vanessa reuses the shared playground workspace and assistant experience contract", () => {
    expect(pageSource).toContain("../../playgrounds/components/PlaygroundWorkspace");
    expect(configSource).toContain("../playgrounds/types");
    expect(configSource).toContain("./assistantExperience");
    expect(configSource).toContain('defaultAssistantRef: VANESSA_CORE_ASSISTANT_EXPERIENCE.assistant_ref');
  });
});
