import { describe, expect, it } from "vitest";
import routesSource from "../../routes/appRoutes.tsx?raw";
import listSource from "./hooks/useAgentProjects.ts?raw";
import detailSource from "./hooks/useAgentProjectEditor.ts?raw";

describe("agent-builder boundaries", () => {
  it("routes point to feature-owned agent builder pages", () => {
    expect(routesSource).toContain('../features/agent-builder/pages/AgentBuilderProjectsPage');
    expect(routesSource).toContain('../features/agent-builder/pages/AgentProjectDetailPage');
  });

  it("builder hooks stay on the agent-projects api contract", () => {
    expect(listSource).toContain('../../../api/agentProjects');
    expect(detailSource).toContain('../../../api/agentProjects');
    expect(listSource).not.toContain('../../../api/catalog');
    expect(detailSource).not.toContain('../../../api/catalog');
  });
});
