import { describe, expect, it } from "vitest";
import type { CatalogTool } from "../../api/catalog";
import { expectLifecycleDefinition } from "../../test/lifecycleGraphAssertions";
import {
  CATALOG_TOOL_LIFECYCLE_STATE_IDS,
  CATALOG_TOOL_LIFECYCLE_TRANSITIONS,
  createCatalogToolLifecycleGraphDefinition,
  getCatalogToolLifecycleState,
} from "./catalogToolLifecycleGraph";

const t = ((key: string) => key) as never;

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
    const definition = createCatalogToolLifecycleGraphDefinition(t);

    expectLifecycleDefinition(definition, {
      stateIds: CATALOG_TOOL_LIFECYCLE_STATE_IDS,
      transitions: CATALOG_TOOL_LIFECYCLE_TRANSITIONS,
      i18nBase: "catalogControl.tools.lifecycle",
    });
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
