import { describe, expect, it } from "vitest";
import {
  buildLifecycleGraphDefinition,
  buildLifecycleEdgePath,
  deriveLifecycleCounts,
  getLifecycleNodeLabelLines,
  resolveLifecycleHighlight,
  type LifecycleGraphDefinition,
} from ".";

const t = ((key: string) => key) as never;

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

  it("builds lifecycle definitions from i18n keys and transition defaults", () => {
    const builtDefinition = buildLifecycleGraphDefinition(t, {
      artifactType: "example",
      stateIds: ["created", "active"],
      i18nBase: "example.lifecycle",
      transitions: [{ from: "created", to: "active" }],
      positions: {
        created: { x: 100, y: 100 },
      },
    });

    expect(builtDefinition).toEqual({
      artifactType: "example",
      states: [
        { id: "created", label: "example.lifecycle.states.created", x: 100, y: 100 },
        { id: "active", label: "example.lifecycle.states.active" },
      ],
      transitions: [
        { from: "created", to: "active", label: "example.lifecycle.transitions.created.active" },
      ],
    });
  });

  it("wraps and truncates long node labels into bounded SVG lines", () => {
    expect(getLifecycleNodeLabelLines("Enabled unbound provider")).toEqual(["Enabled unbound", "provider"]);
    expect(getLifecycleNodeLabelLines("supercalifragilistic")).toEqual(["supercalifrag..."]);
    expect(getLifecycleNodeLabelLines("one two three four five")).toEqual(["one two three", "four five"]);
  });

  it("builds curved edge paths from natural node boundary anchors", () => {
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 300, y: 100 })).toBe("M 170 100 C 190.4 112, 209.6 112, 230 100");
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 100, y: 220 })).toBe("M 100 128 C 88 149.76, 88 170.24, 100 192");
  });
});
