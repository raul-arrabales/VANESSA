import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import HfModelDetailModal from "./HfModelDetailModal";
import type { HfModelDetails } from "../../../api/modelops/types";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";

const richModel: HfModelDetails = {
  source_id: "meta-llama/Llama-3-8B-Instruct",
  name: "Llama 3 8B Instruct",
  sha: "abc123",
  downloads: 42,
  likes: 5,
  author: "meta-llama",
  pipeline_tag: "text-generation",
  library_name: "transformers",
  gated: "manual",
  private: false,
  disabled: false,
  last_modified: "2026-01-03T03:04:00+00:00",
  used_storage: 2048,
  files: [
    {
      path: "model.safetensors",
      size: 1024,
      file_type: "safetensors",
      blob_id: "blob-1",
      lfs: { oid: "sha256:abc", size: 1024 },
    },
    { path: "config.json", size: 256, file_type: "json" },
  ],
  tags: ["llm", "safetensors"],
  card_data: { license: "apache-2.0" },
  config: { model_type: "llama" },
  safetensors: { total: 1 },
  model_index: [{ name: "llama" }],
  transformers_info: { auto_model: "AutoModelForCausalLM" },
};

describe("HfModelDetailModal", () => {
  it("renders identity, file, metadata, and close controls for rich model details", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    await renderWithAppProviders(<HfModelDetailModal model={richModel} onClose={onClose} />);

    const dialog = screen.getByRole("dialog", { name: "meta-llama/Llama-3-8B-Instruct" });
    expect(within(dialog).getByText("Llama 3 8B Instruct")).toBeVisible();
    expect(within(dialog).getByText("meta-llama")).toBeVisible();
    expect(within(dialog).getByText("text-generation")).toBeVisible();
    expect(within(dialog).getByText("transformers")).toBeVisible();
    expect(within(dialog).getByText("42")).toBeVisible();
    expect(within(dialog).getByText("5")).toBeVisible();
    expect(within(dialog).getByText("abc123")).toBeVisible();
    expect(within(dialog).getByText("manual")).toBeVisible();
    expect(within(dialog).getAllByText("no").length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText("llm")).toBeVisible();
    expect(within(dialog).getByText("safetensors")).toBeVisible();
    expect(within(dialog).getByText("safetensors: 1")).toBeVisible();
    expect(within(dialog).getByText("json: 1")).toBeVisible();
    expect(within(dialog).getByText("model.safetensors")).toBeVisible();
    expect(within(dialog).getByText("Type: safetensors · Size: 1,024")).toBeVisible();
    expect(within(dialog).getByText("Blob: blob-1")).toBeVisible();
    expect(within(dialog).getByText(/sha256:abc/)).toBeVisible();
    expect(within(dialog).getByText("config.json")).toBeVisible();
    expect(within(dialog).getByText("Model card data")).toBeVisible();
    expect(within(dialog).getByText("Config")).toBeVisible();
    expect(within(dialog).getByText("Safetensors")).toBeVisible();
    expect(within(dialog).getByText("Model index")).toBeVisible();
    expect(within(dialog).getByText("Transformers info")).toBeVisible();
    expect(within(dialog).getByText(/apache-2.0/)).toBeVisible();

    await user.click(within(dialog).getByRole("button", { name: "Close" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders unavailable and empty states when optional metadata is missing", async () => {
    await renderWithAppProviders(
      <HfModelDetailModal
        model={{
          source_id: "org/minimal-model",
          name: "",
          tags: [],
          files: [],
        }}
        onClose={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "org/minimal-model" });
    expect(within(dialog).getAllByText("Unavailable").length).toBeGreaterThanOrEqual(5);
    expect(within(dialog).getByRole("heading", { name: "Tags" })).toBeVisible();
    expect(within(dialog).getByRole("heading", { name: "File formats" })).toBeVisible();
    expect(within(dialog).getByRole("heading", { name: "Files" })).toBeVisible();
    expect(within(dialog).queryByRole("heading", { name: "Raw metadata" })).not.toBeInTheDocument();
  });
});
