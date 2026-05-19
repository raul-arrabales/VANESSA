import { describe, expect, it } from "vitest";
import type { CatalogMcpServer } from "../../api/catalog";
import { expectLifecycleDefinition } from "../../test/lifecycleGraphAssertions";
import {
  CATALOG_MCP_LIFECYCLE_STATE_IDS,
  CATALOG_MCP_LIFECYCLE_TRANSITIONS,
  createCatalogMcpLifecycleGraphDefinition,
  getCatalogMcpLifecycleState,
} from "./catalogMcpLifecycleGraph";

const t = ((key: string) => key) as never;

function server(overrides: Partial<CatalogMcpServer> = {}): CatalogMcpServer {
  return {
    id: "mcp.example",
    entity: { id: "mcp.example", type: "mcp_server", owner_user_id: 1, visibility: "private" },
    current_version: "v1",
    status: "published",
    published: true,
    published_at: "2026-01-01T00:00:00+00:00",
    spec: {
      name: "Example MCP",
      slug: "example",
      description: "Example MCP server.",
      backing_tool_id: "tool.example",
      exposed_tool_name: "example",
      input_schema: {},
      output_schema: {},
      metadata: {
        category: "custom",
        capabilities: [],
        local: true,
        stateless: true,
        sandboxed: false,
        risk_level: "medium",
        data_access: "none",
        output_freshness: "runtime_generated",
        audit_level: "standard",
      },
      authorization_policy: {
        agent_ids: ["*"],
        agent_domains: ["*"],
        agent_roles: ["*"],
        user_roles: ["*"],
        user_ids: ["*"],
        user_group_ids: ["*"],
      },
      enabled: true,
    },
    validation_status: {
      last_validation_status: "unknown",
      is_validation_current: false,
      validated_version: null,
      last_validated_at: null,
      validation_errors: [],
    },
    ...overrides,
  };
}

describe("catalog MCP lifecycle graph definition", () => {
  it("includes the MCP exposure readiness states and transitions", () => {
    const definition = createCatalogMcpLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: CATALOG_MCP_LIFECYCLE_STATE_IDS,
      transitions: CATALOG_MCP_LIFECYCLE_TRANSITIONS,
      i18nBase: "catalogControl.mcp.lifecycle",
    });
    expect(CATALOG_MCP_LIFECYCLE_TRANSITIONS).toEqual([
      { from: "draft", to: "enabled_unvalidated" },
      { from: "draft", to: "disabled" },
      { from: "disabled", to: "enabled_unvalidated" },
      { from: "enabled_unvalidated", to: "enabled_ready" },
      { from: "enabled_unvalidated", to: "validation_failed" },
      { from: "validation_failed", to: "enabled_unvalidated" },
      { from: "validation_failed", to: "enabled_ready" },
      { from: "enabled_ready", to: "validation_stale" },
      { from: "validation_stale", to: "enabled_ready" },
      { from: "validation_stale", to: "validation_failed" },
      { from: "disabled", to: "draft" },
      { from: "enabled_unvalidated", to: "draft" },
      { from: "validation_failed", to: "draft" },
      { from: "validation_stale", to: "draft" },
      { from: "enabled_ready", to: "draft" },
      { from: "enabled_unvalidated", to: "disabled" },
      { from: "validation_failed", to: "disabled" },
      { from: "validation_stale", to: "disabled" },
      { from: "enabled_ready", to: "disabled" },
    ]);
  });

  it("classifies MCP servers by publication, exposure, and validation readiness", () => {
    expect(getCatalogMcpLifecycleState(server({ published: false }))).toBe("draft");
    expect(getCatalogMcpLifecycleState(server({ spec: { ...server().spec, enabled: false } }))).toBe("disabled");
    expect(getCatalogMcpLifecycleState(server())).toBe("enabled_unvalidated");
    expect(getCatalogMcpLifecycleState(server({
      validation_status: {
        last_validation_status: "failed",
        is_validation_current: true,
        validated_version: "v1",
        last_validated_at: null,
        validation_errors: ["missing backing tool"],
      },
    }))).toBe("validation_failed");
    expect(getCatalogMcpLifecycleState(server({
      validation_status: {
        last_validation_status: "success",
        is_validation_current: false,
        validated_version: "v0",
        last_validated_at: null,
        validation_errors: [],
      },
    }))).toBe("validation_stale");
    expect(getCatalogMcpLifecycleState(server({
      validation_status: {
        last_validation_status: "success",
        is_validation_current: true,
        validated_version: "v1",
        last_validated_at: null,
        validation_errors: [],
      },
    }))).toBe("enabled_ready");
  });
});
