import { describe, expect, it } from "vitest";
import type { CatalogTool } from "../../api/catalog";
import { CATALOG_TOOL_LIFECYCLE_STATE_IDS, CATALOG_TOOL_LIFECYCLE_TRANSITIONS, getCatalogToolLifecycleState } from "./catalogToolLifecycleGraph";

function tool(overrides: Partial<CatalogTool> = {}): CatalogTool {
  return {
    id: "tool.example",
    entity: { id: "tool.example", type: "tool", owner_user_id: 1, visibility: "private" },
    current_version: "v1",
    status: "draft",
    published: false,
    published_at: null,
    spec: {
      name: "Example",
      description: "Example tool",
      input_schema: {},
      output_schema: {},
      safety_policy: {},
      offline_compatible: true,
      execution_backend: "internal_http",
      execution_config: {},
      permissions: {},
    },
    ...overrides,
  };
}

describe("catalog tool lifecycle graph definition", () => {
  it("includes the tool readiness states and transitions", () => {
    expect(CATALOG_TOOL_LIFECYCLE_STATE_IDS).toEqual([
      "draft",
      "published_unvalidated",
      "validation_failed",
      "validation_stale",
      "ready",
    ]);
    expect(CATALOG_TOOL_LIFECYCLE_TRANSITIONS).toEqual([
      { from: "draft", to: "published_unvalidated" },
      { from: "published_unvalidated", to: "ready" },
      { from: "published_unvalidated", to: "validation_failed" },
      { from: "validation_failed", to: "published_unvalidated" },
      { from: "validation_failed", to: "ready" },
      { from: "ready", to: "validation_stale" },
      { from: "validation_stale", to: "ready" },
      { from: "validation_stale", to: "validation_failed" },
      { from: "published_unvalidated", to: "draft" },
      { from: "validation_failed", to: "draft" },
      { from: "validation_stale", to: "draft" },
      { from: "ready", to: "draft" },
    ]);
  });

  it("classifies tools by publish and validation readiness", () => {
    expect(getCatalogToolLifecycleState(tool())).toBe("draft");
    expect(getCatalogToolLifecycleState(tool({ published: true }))).toBe("published_unvalidated");
    expect(getCatalogToolLifecycleState(tool({
      published: true,
      validation_status: {
        last_validation_status: "failed",
        is_validation_current: true,
        validated_version: "v1",
        last_validated_at: null,
        validation_errors: ["missing backend"],
      },
    }))).toBe("validation_failed");
    expect(getCatalogToolLifecycleState(tool({
      published: true,
      validation_status: {
        last_validation_status: "success",
        is_validation_current: false,
        validated_version: "v0",
        last_validated_at: null,
        validation_errors: [],
      },
    }))).toBe("validation_stale");
    expect(getCatalogToolLifecycleState(tool({
      published: true,
      validation_status: {
        last_validation_status: "success",
        is_validation_current: true,
        validated_version: "v1",
        last_validated_at: null,
        validation_errors: [],
      },
    }))).toBe("ready");
  });
});
