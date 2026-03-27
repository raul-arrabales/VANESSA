import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import contextKnowledgeBasesPageSource from "../../pages/ContextKnowledgeBasesPage.tsx?raw";
import contextKnowledgeBaseCreatePageSource from "../../pages/ContextKnowledgeBaseCreatePage.tsx?raw";
import contextKnowledgeBaseDetailPageSource from "../../pages/ContextKnowledgeBaseDetailPage.tsx?raw";

describe("context-management boundaries", () => {
  it("keeps routes pointed at feature-domain context pages", () => {
    expect(routesSource).toContain("../features/context-management/pages/ContextKnowledgeBasesPage");
    expect(routesSource).toContain("../features/context-management/pages/ContextKnowledgeBaseCreatePage");
    expect(routesSource).toContain("../features/context-management/pages/ContextKnowledgeBaseDetailPage");
    expect(routesSource).not.toContain("../pages/ContextKnowledgeBasesPage");
    expect(routesSource).not.toContain("../pages/ContextKnowledgeBaseCreatePage");
    expect(routesSource).not.toContain("../pages/ContextKnowledgeBaseDetailPage");
  });

  it("keeps legacy context page files as thin feature wrappers", () => {
    const pageSources = [
      contextKnowledgeBasesPageSource,
      contextKnowledgeBaseCreatePageSource,
      contextKnowledgeBaseDetailPageSource,
    ];

    for (const source of pageSources) {
      expect(source).toContain('export { default } from "../features/context-management/pages/');
      expect(source).not.toContain("../api/context");
      expect(source).not.toContain("useState");
      expect(source).not.toContain("useEffect");
    }
  });
});
