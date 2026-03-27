import { describe, expect, it } from "vitest";
import { appRoutes } from "./appRoutes";

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
      "/control/agent-builder",
      "/control/agent-builder/:projectId",
      "/control/catalog",
      "/control/system-health",
      "/control/platform",
      "/control/platform/providers",
      "/control/platform/providers/new",
      "/control/platform/providers/:providerId",
      "/control/platform/deployments",
      "/control/platform/deployments/new",
      "/control/platform/deployments/:deploymentId",
      "/control/context",
      "/control/context/new",
      "/control/context/:knowledgeBaseId",
      "/control/models",
      "/control/models/catalog",
      "/control/models/cloud/register",
      "/control/models/local/register",
      "/control/models/local/artifacts",
      "/control/models/access",
      "/control/models/:modelId/test",
      "/control/models/:modelId",
      "/ai",
      "/ai/chat",
      "/ai/knowledge",
    ]);
  });

});
