import type {
  KnowledgeBase,
  KnowledgeBaseChunkingStrategy,
  KnowledgeBaseEmbeddingResourceSummary,
  KnowledgeBaseVectorizationMode,
  KnowledgeBaseVectorizationOptions,
} from "../../api/context";

export type ChunkingFormState = {
  strategy: KnowledgeBaseChunkingStrategy;
  chunkLength: string;
  chunkOverlap: string;
};

export type ChunkingFormTouchedState = {
  chunkLengthTouched: boolean;
  chunkOverlapTouched: boolean;
};

type ChunkingValidationError = {
  key: string;
  values?: Record<string, number | string>;
};

type ChunkingValidationSuccess = {
  ok: true;
  normalizedChunking: {
    strategy: "fixed_length";
    config: {
      unit: "tokens";
      chunk_length: number;
      chunk_overlap: number;
    };
  };
};

type ChunkingValidationFailure = {
  ok: false;
  error: ChunkingValidationError;
};

export type ChunkingValidationResult = ChunkingValidationSuccess | ChunkingValidationFailure;

export const DEFAULT_CHUNKING_FORM_STATE: ChunkingFormState = {
  strategy: "fixed_length",
  chunkLength: "300",
  chunkOverlap: "60",
};

export function createDefaultChunkingFormState(): ChunkingFormState {
  return { ...DEFAULT_CHUNKING_FORM_STATE };
}

export function createChunkingFormStateFromKnowledgeBase(knowledgeBase: KnowledgeBase): ChunkingFormState {
  return {
    strategy: knowledgeBase.chunking.strategy === "fixed_length" ? "fixed_length" : "fixed_length",
    chunkLength: String(knowledgeBase.chunking.config.chunk_length),
    chunkOverlap: String(knowledgeBase.chunking.config.chunk_overlap),
  };
}

export function resolveSelectedEmbeddingResource(
  vectorizationOptions: KnowledgeBaseVectorizationOptions | null,
  selectedEmbeddingProviderId: string,
  selectedEmbeddingResourceId: string,
): KnowledgeBaseEmbeddingResourceSummary | null {
  const selectedProvider = vectorizationOptions?.embedding_providers.find((provider) => provider.id === selectedEmbeddingProviderId) ?? null;
  return selectedProvider?.resources.find((resource) => resource.id === selectedEmbeddingResourceId) ?? null;
}

export function resolveSelectedEmbeddingChunkingConstraints(
  vectorizationOptions: KnowledgeBaseVectorizationOptions | null,
  selectedEmbeddingProviderId: string,
  selectedEmbeddingResourceId: string,
): NonNullable<KnowledgeBaseEmbeddingResourceSummary["chunking_constraints"]> | null {
  return resolveSelectedEmbeddingResource(
    vectorizationOptions,
    selectedEmbeddingProviderId,
    selectedEmbeddingResourceId,
  )?.chunking_constraints ?? null;
}

export function autoSeedChunkingFormState(args: {
  form: ChunkingFormState;
  touched: ChunkingFormTouchedState;
  selectedVectorizationMode: KnowledgeBaseVectorizationMode;
  selectedEmbeddingSafeChunkLengthMax: number | null;
}): ChunkingFormState | null {
  const { form, touched, selectedVectorizationMode, selectedEmbeddingSafeChunkLengthMax } = args;
  if (
    selectedVectorizationMode !== "vanessa_embeddings"
    || selectedEmbeddingSafeChunkLengthMax == null
    || selectedEmbeddingSafeChunkLengthMax >= 300
  ) {
    return null;
  }
  let nextForm: ChunkingFormState | null = null;
  const nextChunkLength = String(selectedEmbeddingSafeChunkLengthMax);
  const nextChunkOverlap = String(Math.min(60, Math.max(0, selectedEmbeddingSafeChunkLengthMax - 1)));
  if (
    !touched.chunkLengthTouched
    && Number.parseInt(form.chunkLength, 10) === 300
    && form.chunkLength !== nextChunkLength
  ) {
    nextForm = {
      ...(nextForm ?? form),
      chunkLength: nextChunkLength,
    };
  }
  if (
    !touched.chunkOverlapTouched
    && Number.parseInt(form.chunkOverlap, 10) === 60
    && form.chunkOverlap !== nextChunkOverlap
  ) {
    nextForm = {
      ...(nextForm ?? form),
      chunkOverlap: nextChunkOverlap,
    };
  }
  return nextForm;
}

export function validateChunkingFormState(args: {
  form: ChunkingFormState;
  selectedVectorizationMode: KnowledgeBaseVectorizationMode;
  selectedEmbeddingSafeChunkLengthMax: number | null;
}): ChunkingValidationResult {
  const { form, selectedVectorizationMode, selectedEmbeddingSafeChunkLengthMax } = args;
  if (form.strategy !== "fixed_length") {
    return {
      ok: false,
      error: { key: "contextManagement.feedback.chunkingStrategyRequired" },
    };
  }
  const normalizedChunkLength = Number.parseInt(form.chunkLength, 10);
  if (!Number.isInteger(normalizedChunkLength) || normalizedChunkLength <= 0) {
    return {
      ok: false,
      error: { key: "contextManagement.feedback.chunkLengthInvalid" },
    };
  }
  const normalizedChunkOverlap = Number.parseInt(form.chunkOverlap, 10);
  if (!Number.isInteger(normalizedChunkOverlap) || normalizedChunkOverlap < 0) {
    return {
      ok: false,
      error: { key: "contextManagement.feedback.chunkOverlapInvalid" },
    };
  }
  if (normalizedChunkOverlap >= normalizedChunkLength) {
    return {
      ok: false,
      error: { key: "contextManagement.feedback.chunkOverlapTooLarge" },
    };
  }
  if (
    selectedVectorizationMode === "vanessa_embeddings"
    && selectedEmbeddingSafeChunkLengthMax != null
    && normalizedChunkLength > selectedEmbeddingSafeChunkLengthMax
  ) {
    return {
      ok: false,
      error: {
        key: "contextManagement.feedback.chunkLengthExceedsModelLimit",
        values: {
          chunkLength: normalizedChunkLength,
          safeChunkLengthMax: selectedEmbeddingSafeChunkLengthMax,
        },
      },
    };
  }
  return {
    ok: true,
    normalizedChunking: {
      strategy: "fixed_length",
      config: {
        unit: "tokens",
        chunk_length: normalizedChunkLength,
        chunk_overlap: normalizedChunkOverlap,
      },
    },
  };
}
