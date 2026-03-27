import { describe, expect, it } from "vitest";
import type { PreviewableAssistantExperience } from "./assistantExperience";
import { buildAgentProjectPreview, DEFAULT_AGENT_PROJECT_FORM } from "../agent-builder/types";
import { VANESSA_CORE_ASSISTANT_EXPERIENCE } from "../vanessa-core/assistantExperience";

describe("assistant experience contract", () => {
  it("keeps builder preview aligned with the shared snake_case assistant experience shape", () => {
    const preview: PreviewableAssistantExperience = buildAgentProjectPreview("proj-1", {
      ...DEFAULT_AGENT_PROJECT_FORM,
      defaultModelRef: "safe-small",
      toolRefsText: "tool.web_search, tool.files",
    });

    expect(preview).toEqual({
      assistant_ref: "agent.project.proj-1",
      playground_kind: "chat",
      default_model_ref: "safe-small",
      tool_refs: ["tool.web_search", "tool.files"],
      runtime_constraints: {
        internet_required: false,
        sandbox_required: false,
      },
      workflow_definition: {
        entrypoint: "assistant",
      },
    });
    expect("assistantRef" in preview).toBe(false);
    expect("defaultModelRef" in preview).toBe(false);
  });

  it("lets Vanessa reuse the same assistant experience contract as builder preview", () => {
    const vanessa: PreviewableAssistantExperience = VANESSA_CORE_ASSISTANT_EXPERIENCE;

    expect(vanessa.assistant_ref).toBe("assistant.vanessa.core");
    expect(vanessa.playground_kind).toBe("chat");
    expect(vanessa.tool_refs).toEqual([]);
    expect(vanessa.workflow_definition).toEqual({
      entrypoint: "assistant",
      assistant_variant: "vanessa_core",
    });
  });
});
