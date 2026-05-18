import { describe, expect, it } from "vitest";
import { deriveLifecycleCounts, resolveLifecycleHighlight, type LifecycleGraphDefinition } from "./LifecycleGraph";

const definition: LifecycleGraphDefinition = {
  artifactType: "test",
  states: [
    { id: "created", label: "Created" },
    { id: "active", label: "Active" },
  ],
  transitions: [
    { from: "created", to: "active" },
  ],
};

describe("LifecycleGraph utilities", () => {
  it("groups known states and counts unknown or missing states separately", () => {
    const counts = deriveLifecycleCounts(
      [
        { state: "created" },
        { state: "active" },
        { state: "ACTIVE" },
        { state: "mystery" },
        { state: null },
      ],
      definition,
      (item) => item.state,
    );

    expect(counts).toEqual({
      byState: {
        created: 1,
        active: 2,
      },
      unknown: 2,
    });
  });

  it("highlights the current state and outgoing transitions", () => {
    const highlight = resolveLifecycleHighlight({ state: "created" }, definition, (item) => item.state);

    expect(highlight.currentState).toBe("created");
    expect(highlight.outgoingTransitions.has("created->active")).toBe(true);
  });
});
