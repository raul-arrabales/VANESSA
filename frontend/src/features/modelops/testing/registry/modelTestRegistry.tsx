import type { ModelTestRegistryEntry } from "../types";
import EmbeddingModelTestPanel from "../panels/EmbeddingModelTestPanel";
import LLMModelTestPanel from "../panels/LLMModelTestPanel";

export const modelTestRegistry: Record<string, ModelTestRegistryEntry> = {
  llm: {
    defaultInputs: { prompt: "hello" },
    buildRequest: (inputs) => ({ prompt: String(inputs.prompt ?? "").trim() }),
    summarizeResult: (result, latestTest) => result?.response_text || latestTest?.summary || "",
    formatDebugPayload: (latestTest) => ({
      requestPayload: latestTest?.input_payload ?? {},
      responsePayload: latestTest?.output_payload ?? latestTest?.error_details ?? {},
    }),
    renderPanel: ({ isPending, defaultInputs, runDisabled, onRun }) => (
      <LLMModelTestPanel
        isPending={isPending}
        defaultInputs={{ prompt: String(defaultInputs.prompt ?? "hello") }}
        runDisabled={runDisabled}
        onRun={async (inputs) => {
          await onRun(inputs);
        }}
      />
    ),
  },
  embeddings: {
    defaultInputs: { text: "hello world" },
    buildRequest: (inputs) => ({ text: String(inputs.text ?? "").trim() }),
    summarizeResult: (result, latestTest) => {
      if (typeof result?.dimension === "number") {
        return `Embedding returned (${result.dimension} dims)`;
      }
      return latestTest?.summary || "";
    },
    formatDebugPayload: (latestTest) => ({
      requestPayload: latestTest?.input_payload ?? {},
      responsePayload: latestTest?.output_payload ?? latestTest?.error_details ?? {},
    }),
    renderPanel: ({ isPending, defaultInputs, runDisabled, onRun }) => (
      <EmbeddingModelTestPanel
        isPending={isPending}
        defaultInputs={{ text: String(defaultInputs.text ?? "hello world") }}
        runDisabled={runDisabled}
        onRun={async (inputs) => {
          await onRun(inputs);
        }}
      />
    ),
  },
};
