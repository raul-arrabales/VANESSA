import type { JSX } from "react";
import EmbeddingModelTestPanel from "./components/EmbeddingModelTestPanel";
import LLMModelTestPanel from "./components/LLMModelTestPanel";

export type ModelTestPanelRendererProps = {
  isPending: boolean;
  onRun: (inputs: Record<string, unknown>) => Promise<void>;
};

type ModelTestRegistryEntry = {
  renderPanel: (props: ModelTestPanelRendererProps) => JSX.Element;
};

export const modelTestRegistry: Record<string, ModelTestRegistryEntry> = {
  llm: {
    renderPanel: ({ isPending, onRun }) => (
      <LLMModelTestPanel
        isPending={isPending}
        onRun={async (inputs) => {
          await onRun(inputs);
        }}
      />
    ),
  },
  embeddings: {
    renderPanel: ({ isPending, onRun }) => (
      <EmbeddingModelTestPanel
        isPending={isPending}
        onRun={async (inputs) => {
          await onRun(inputs);
        }}
      />
    ),
  },
};
