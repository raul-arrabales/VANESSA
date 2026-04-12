import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LocalDiscoveryPanel from "./LocalDiscoveryPanel";
import LocalDownloadsPanel from "./LocalDownloadsPanel";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

describe("LocalDiscoveryPanel", () => {
  it("localizes discovery list aria labels", async () => {
    await renderWithAppProviders(
      <LocalDiscoveryPanel
        taskKey="llm"
        query=""
        feedback=""
        discoveredModels={[]}
        selectedModelInfo=""
        onTaskKeyChange={vi.fn()}
        onQueryChange={vi.fn()}
        onSearch={vi.fn(async () => undefined)}
        onInspect={vi.fn(async () => undefined)}
        onDownload={vi.fn(async () => undefined)}
      />,
      { language: "es" },
    );

    expect(screen.getByRole("list", { name: "Resultados del descubrimiento local" })).toBeVisible();
    expect(screen.queryByRole("list", { name: "Trabajos de descarga" })).not.toBeInTheDocument();
  });

  it("localizes download list aria labels", async () => {
    await renderWithAppProviders(
      <LocalDownloadsPanel
        downloadJobs={[]}
        hasActiveJobs={false}
      />,
      { language: "es" },
    );

    expect(screen.getByRole("heading", { name: "Descargas activas" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Trabajos de descarga" })).toBeVisible();
  });
});
