import { screen, within } from "@testing-library/react";

export async function findShellSidebar(navLabel: string): Promise<HTMLElement> {
  return screen.findByRole("navigation", { name: navLabel });
}

export async function findShellPathCue(pathLabel: string): Promise<HTMLElement> {
  return screen.findByLabelText(pathLabel);
}

export async function findShellSidebarRegion(): Promise<HTMLElement> {
  return screen.findByTestId("app-sidebar");
}

export function withinShellRegion(element: HTMLElement) {
  return within(element);
}
