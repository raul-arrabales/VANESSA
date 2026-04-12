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
        completedSearchId={0}
        completedLoadMoreId={0}
        latestLoadedBatchStartIndex={null}
        canLoadMoreModels={false}
        isLoadingMoreModels={false}
        onTaskKeyChange={vi.fn()}
        onQueryChange={vi.fn()}
        onSearch={vi.fn(async () => undefined)}
        onLoadMore={vi.fn(async () => undefined)}
        onInspect={vi.fn(async () => undefined)}
        onDownload={vi.fn(async () => undefined)}
      />,
      { language: "es" },
    );

    expect(screen.getByRole("list", { name: "Resultados del descubrimiento local" })).toBeVisible();
    expect(screen.queryByRole("list", { name: "Trabajos de descarga" })).not.toBeInTheDocument();
  });

  it("renders discovery result actions before the model metadata", async () => {
    await renderWithAppProviders(
      <LocalDiscoveryPanel
        taskKey="llm"
        query=""
        feedback=""
        discoveredModels={[
          {
            source_id: "meta-llama/Llama-3-8B-Instruct",
            name: "Llama 3 8B Instruct",
            downloads: 42,
            likes: 5,
            tags: ["llm"],
            provider: "huggingface",
          },
        ]}
        completedSearchId={0}
        completedLoadMoreId={0}
        latestLoadedBatchStartIndex={null}
        canLoadMoreModels={true}
        isLoadingMoreModels={false}
        onTaskKeyChange={vi.fn()}
        onQueryChange={vi.fn()}
        onSearch={vi.fn(async () => undefined)}
        onLoadMore={vi.fn(async () => undefined)}
        onInspect={vi.fn(async () => undefined)}
        onDownload={vi.fn(async () => undefined)}
      />,
    );

    const inspectButton = screen.getByRole("button", { name: "Inspect" });
    const modelName = screen.getByText("meta-llama/Llama-3-8B-Instruct");
    expect(inspectButton.compareDocumentPosition(modelName) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("1.")).toBeVisible();
    expect(screen.getByText("42 downloads · 5 likes")).toBeVisible();
    expect(screen.getByRole("button", { name: "Load more matches" })).toBeVisible();
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
