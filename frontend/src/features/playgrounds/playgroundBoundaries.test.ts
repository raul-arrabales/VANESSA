import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";

const apiModules = import.meta.glob("../../api/*.ts");
const apiModuleKeys = Object.keys(apiModules);

describe("playground boundaries", () => {
  it("removes the legacy playground compatibility API files", () => {
    expect(apiModuleKeys).not.toContain("../../api/chat.ts");
    expect(apiModuleKeys).not.toContain("../../api/knowledge.ts");
  });

  it("keeps app routes pointed at feature-domain playground pages", () => {
    expect(routesSource).toContain("../features/playgrounds/pages/ChatPlaygroundPage");
    expect(routesSource).toContain("../features/playgrounds/pages/KnowledgePlaygroundPage");
    expect(routesSource).not.toContain("../pages/ChatbotPage");
    expect(routesSource).not.toContain("../pages/KnowledgeChatPage");
  });
});
