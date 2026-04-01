import { describe, expect, it } from "vitest";
import {
  autoSeedChunkingFormState,
  createChunkingFormStateFromKnowledgeBase,
  createDefaultChunkingFormState,
  resolveSelectedEmbeddingChunkingConstraints,
  validateChunkingFormState,
} from "./chunkingForm";

describe("chunkingForm", () => {
  it("creates the default chunking form state", () => {
    expect(createDefaultChunkingFormState()).toEqual({
      strategy: "fixed_length",
      chunkLength: "300",
      chunkOverlap: "60",
    });
  });

  it("creates chunking form state from an existing knowledge base", () => {
    expect(createChunkingFormStateFromKnowledgeBase({
      chunking: {
        strategy: "fixed_length",
        config: {
          unit: "tokens",
          chunk_length: 254,
          chunk_overlap: 32,
        },
      },
    } as never)).toEqual({
      strategy: "fixed_length",
      chunkLength: "254",
      chunkOverlap: "32",
    });
  });

  it("resolves the selected embeddings resource constraints", () => {
    expect(resolveSelectedEmbeddingChunkingConstraints({
      backing_provider: null,
      supports_named_vectors: true,
      supported_modes: [],
      embedding_providers: [
        {
          id: "embedding-provider-1",
          resources: [
            {
              id: "text-embedding-3-small",
              chunking_constraints: {
                max_input_tokens: 256,
                special_tokens_per_input: 2,
                safe_chunk_length_max: 254,
              },
            },
          ],
        },
      ],
    }, "embedding-provider-1", "text-embedding-3-small")).toEqual({
      max_input_tokens: 256,
      special_tokens_per_input: 2,
      safe_chunk_length_max: 254,
    });
  });

  it("auto-seeds untouched defaults when the selected embeddings model safe max is lower", () => {
    expect(autoSeedChunkingFormState({
      form: createDefaultChunkingFormState(),
      touched: {
        chunkLengthTouched: false,
        chunkOverlapTouched: false,
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      strategy: "fixed_length",
      chunkLength: "254",
      chunkOverlap: "60",
    });
  });

  it("validates successful chunking state", () => {
    expect(validateChunkingFormState({
      form: {
        strategy: "fixed_length",
        chunkLength: "254",
        chunkOverlap: "60",
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      ok: true,
      normalizedChunking: {
        strategy: "fixed_length",
        config: {
          unit: "tokens",
          chunk_length: 254,
          chunk_overlap: 60,
        },
      },
    });
  });

  it("rejects invalid chunking values and safe-max overflow", () => {
    expect(validateChunkingFormState({
      form: {
        strategy: "fixed_length",
        chunkLength: "0",
        chunkOverlap: "60",
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      ok: false,
      error: { key: "contextManagement.feedback.chunkLengthInvalid" },
    });

    expect(validateChunkingFormState({
      form: {
        strategy: "fixed_length",
        chunkLength: "254",
        chunkOverlap: "-1",
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      ok: false,
      error: { key: "contextManagement.feedback.chunkOverlapInvalid" },
    });

    expect(validateChunkingFormState({
      form: {
        strategy: "fixed_length",
        chunkLength: "254",
        chunkOverlap: "254",
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      ok: false,
      error: { key: "contextManagement.feedback.chunkOverlapTooLarge" },
    });

    expect(validateChunkingFormState({
      form: {
        strategy: "fixed_length",
        chunkLength: "300",
        chunkOverlap: "60",
      },
      selectedVectorizationMode: "vanessa_embeddings",
      selectedEmbeddingSafeChunkLengthMax: 254,
    })).toEqual({
      ok: false,
      error: {
        key: "contextManagement.feedback.chunkLengthExceedsModelLimit",
        values: {
          chunkLength: 300,
          safeChunkLengthMax: 254,
        },
      },
    });
  });
});
