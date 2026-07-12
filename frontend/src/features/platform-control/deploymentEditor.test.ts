import { describe, expect, it } from "vitest";
import { removeCapabilityFromDeploymentForm, type DeploymentFormState } from "./deploymentEditor";

describe("removeCapabilityFromDeploymentForm", () => {
  it("removes only the selected capability while preserving unsaved edits", () => {
    const form: DeploymentFormState = {
      slug: "edited-slug",
      displayName: "Unsaved name",
      description: "Unsaved description",
      capabilityKeys: ["llm_inference", "web_search"],
      providerIdsByCapability: { llm_inference: "llm", web_search: "search" },
      resourceIdsByCapability: { llm_inference: ["model"], web_search: ["index"] },
      defaultResourceIdsByCapability: { llm_inference: "model", web_search: "index" },
      resourcePolicyByCapability: { llm_inference: {}, web_search: { selection_mode: "explicit" } },
    };

    expect(removeCapabilityFromDeploymentForm(form, "web_search")).toEqual({
      slug: "edited-slug",
      displayName: "Unsaved name",
      description: "Unsaved description",
      capabilityKeys: ["llm_inference"],
      providerIdsByCapability: { llm_inference: "llm" },
      resourceIdsByCapability: { llm_inference: ["model"] },
      defaultResourceIdsByCapability: { llm_inference: "model" },
      resourcePolicyByCapability: { llm_inference: {} },
    });
  });
});
