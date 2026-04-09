import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LocalDiscoveryPanel from "./LocalDiscoveryPanel";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

describe("LocalDiscoveryPanel", () => {
  it("localizes discovery and download list aria labels", async () => {
    await renderWithAppProviders(
      <LocalDiscoveryPanel
        taskKey="llm"
        query=""
        discoveredModels={[]}
        selectedModelInfo=""
        downloadJobs={[]}
        hasActiveJobs={false}
        onTaskKeyChange={vi.fn()}
        onQueryChange={vi.fn()}
        onSearch={vi.fn(async () => undefined)}
        onInspect={vi.fn(async () => undefined)}
        onDownload={vi.fn(async () => undefined)}
      />,
      { language: "es" },
    );

    expect(screen.getByRole("list", { name: "Resultados del descubrimiento local" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Trabajos de descarga" })).toBeVisible();
  });
});
