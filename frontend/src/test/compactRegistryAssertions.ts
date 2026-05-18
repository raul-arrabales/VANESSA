import { screen } from "@testing-library/react";
import { expect } from "vitest";

type ActionRole = "button" | "link";

export function expectCompactRegistryRowForHeading(name: string): void {
  expect(screen.getByRole("heading", { name }).closest(".compact-registry-item")).toBeTruthy();
}

export function expectNamedIconAction(role: ActionRole, name: string): HTMLElement {
  const action = screen.getByRole(role, { name });
  expect(action).toHaveAttribute("title", name);
  return action;
}

export function expectNoGenericCompactActions(names: string[] = ["Edit", "Delete", "Validate", "Test"]): void {
  for (const name of names) {
    expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name })).not.toBeInTheDocument();
  }
}
