import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LifecycleGraph, type LifecycleGraphDefinition } from ".";

describe("LifecycleGraph rendering", () => {
  it("renders long labels across bounded SVG text lines", () => {
    const definition: LifecycleGraphDefinition = {
      artifactType: "visual-test",
      states: [
        { id: "enabled_unbound", label: "Enabled unbound provider", x: 120, y: 90 },
        { id: "active_attention", label: "Active attention", x: 320, y: 90 },
      ],
      transitions: [
        { from: "enabled_unbound", to: "active_attention", label: "Activate" },
      ],
    };

    render(<LifecycleGraph definition={definition} currentState="enabled_unbound" />);

    const graph = screen.getByRole("img", { name: "visual-test lifecycle graph" });
    expect(within(graph).getByText("Enabled unbound")).toBeInTheDocument();
    expect(within(graph).getByText("provider")).toBeInTheDocument();
  });
});
