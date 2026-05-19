import { describe, expect, it } from "vitest";
import type { CatalogAgent, CatalogAgentValidation } from "../../api/catalog";
import { CATALOG_AGENT_LIFECYCLE_STATE_IDS, CATALOG_AGENT_LIFECYCLE_TRANSITIONS, getCatalogAgentLifecycleState } from "./catalogAgentLifecycleGraph";

function agent(overrides: Partial<CatalogAgent> = {}): CatalogAgent {
  return {
    id: "agent.example",
    entity: { id: "agent.example", type: "agent", owner_user_id: 1, visibility: "private" },
    agent_kind: "platform",
    is_platform_agent: true,
    current_version: "v1",
    status: "published",
    published: true,
    published_at: "2026-01-01T00:00:00+00:00",
    spec: {
      name: "Example agent",
      description: "Example catalog agent.",
      instructions: "Be useful.",
      runtime_prompts: { retrieval_context: "" },
      default_model_ref: "model.safe",
      tool_refs: ["tool.web_search"],
      mcp_server_refs: ["web_search"],
      agent_domain: "default",
      runtime_constraints: { internet_required: true, sandbox_required: false },
    },
    ...overrides,
  };
}

function validation(valid: boolean): CatalogAgentValidation {
  return {
    agent: agent(),
    validation: {
      valid,
      errors: valid ? [] : ["missing model"],
      warnings: [],
      resolved_tools: [],
      resolved_mcp_servers: [],
      derived_runtime_requirements: {
        internet_required: true,
        sandbox_required: false,
      },
    },
  };
}

describe("catalog agent lifecycle graph definition", () => {
  it("includes the agent lifecycle states and transitions", () => {
    expect(CATALOG_AGENT_LIFECYCLE_STATE_IDS).toEqual([
      "draft",
      "published_unvalidated",
      "validation_failed",
      "ready",
    ]);
    expect(CATALOG_AGENT_LIFECYCLE_TRANSITIONS).toEqual([
      { from: "draft", to: "published_unvalidated" },
      { from: "published_unvalidated", to: "ready" },
      { from: "published_unvalidated", to: "validation_failed" },
      { from: "validation_failed", to: "published_unvalidated" },
      { from: "validation_failed", to: "ready" },
      { from: "published_unvalidated", to: "draft" },
      { from: "validation_failed", to: "draft" },
      { from: "ready", to: "draft" },
    ]);
  });

  it("classifies agents by publish and current validation result", () => {
    expect(getCatalogAgentLifecycleState(agent({ published: false }))).toBe("draft");
    expect(getCatalogAgentLifecycleState(agent())).toBe("published_unvalidated");
    expect(getCatalogAgentLifecycleState(agent(), validation(false))).toBe("validation_failed");
    expect(getCatalogAgentLifecycleState(agent(), validation(true))).toBe("ready");
  });
});
