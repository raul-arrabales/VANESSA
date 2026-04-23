import { describe, expect, it } from "vitest";
import type { CatalogTool } from "../../api/catalog";
import { buildSampleToolInput } from "./catalogToolTestSamples";

function buildTool(overrides: Partial<CatalogTool> = {}): CatalogTool {
  return {
    id: "tool.example",
    entity: { id: "tool.example", type: "tool", owner_user_id: 1, visibility: "private" },
    current_version: "v1",
    status: "draft",
    published: false,
    published_at: null,
    spec: {
      name: "Example",
      description: "desc",
      transport: "mcp",
      connection_profile_ref: "default",
      tool_name: "example_tool",
      input_schema: {},
      output_schema: {},
      safety_policy: {},
      offline_compatible: false,
    },
    ...overrides,
  };
}

describe("buildSampleToolInput", () => {
  it("returns the curated web search sample", () => {
    expect(buildSampleToolInput(buildTool({
      id: "tool.web_search",
      spec: {
        ...buildTool().spec,
        tool_name: "web_search",
      },
    }))).toEqual({
      query: "OpenAI platform runtime",
      top_k: 3,
    });
  });

  it("returns the curated python execution sample", () => {
    expect(buildSampleToolInput(buildTool({
      id: "tool.python_exec",
      spec: {
        ...buildTool().spec,
        transport: "sandbox_http",
        tool_name: "python_exec",
      },
    }))).toEqual({
      code: "numbers = input_payload.get('numbers', [1, 2, 3])\nresult = sum(numbers)\nprint(f'Sum: {result}')",
      input: {
        numbers: [1, 2, 3],
      },
      timeout_seconds: 5,
    });
  });

  it("builds a generic schema-based sample for other tools", () => {
    expect(buildSampleToolInput(buildTool({
      spec: {
        ...buildTool().spec,
        input_schema: {
          type: "object",
          properties: {
            prompt: { type: "string" },
            top_k: { type: "integer", minimum: 2 },
          },
          required: ["prompt", "top_k"],
        },
      },
    }))).toEqual({
      prompt: "example",
      top_k: 2,
    });
  });
});
