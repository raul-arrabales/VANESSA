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

  it("uses straight edge paths for adjacent node connections", () => {
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 300, y: 100 })).toBe("M 170 100 L 230 100");
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 100, y: 220 })).toBe("M 100 128 L 100 192");
  });

  it("keeps distant node connections curved", () => {
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 500, y: 100 })).toBe("M 170 100 C 258.4 131.2, 341.6 131.2, 430 100");
  });

  it("separates reciprocal edge paths into parallel lanes", () => {
    expect(buildLifecycleEdgePath({ x: 100, y: 100 }, { x: 300, y: 100 }, { laneOffset: 6 })).toBe("M 170 106 L 230 106");
    expect(buildLifecycleEdgePath({ x: 300, y: 100 }, { x: 100, y: 100 }, { laneOffset: 6 })).toBe("M 230 94 L 170 94");
  });
});
