import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ManagedModel } from "../../api/modelops/types";
import type { PlatformProvider } from "../../api/platform";
import { usePlatformProviderLoadState } from "./hooks/usePlatformProviderLoadState";
import { buildProviderLoadDisplayData } from "./providerLoad";

function buildProvider(overrides: Partial<PlatformProvider> = {}): PlatformProvider {
  return {
    id: "provider-1",
    slug: "provider-1",
    provider_key: "vllm_embeddings_local",
    capability: "embeddings",
    adapter_kind: "openai_compatible_embeddings",
    display_name: "vLLM embeddings local",
    description: "Embeddings runtime",
    endpoint_url: "http://llm:8000",
    healthcheck_url: "http://llm:8000/health",
    enabled: true,
    config: {},
    secret_refs: {},
    loaded_managed_model_id: null,
    loaded_managed_model_name: null,
    loaded_runtime_model_id: null,
    loaded_local_path: null,
    loaded_source_id: null,
    load_state: "empty",
    load_error: null,
    ...overrides,
  };
}

function buildLocalModel(overrides: Partial<ManagedModel> = {}): ManagedModel {
  return {
    id: "sentence-transformers--all-MiniLM-L6-v2",
    name: "all-MiniLM-L6-v2",
    provider: "huggingface",
    backend: "local",
    source: "huggingface",
    availability: "offline_ready",
    task_key: "embeddings",
    category: "predictive",
    lifecycle_state: "active",
    is_validation_current: true,
    last_validation_status: "success",
    ...overrides,
  };
}

function translate(key: string, options: Record<string, unknown> = {}): string {
  const dictionary: Record<string, string> = {
    "platformControl.summary.none": "None",
    "platformControl.providers.loadedModelStateHintEmpty": "Empty state hint",
    "platformControl.providers.loadedModelStateHintLoading": "Loading state hint",
    "platformControl.providers.loadedModelStateHintReconciling": "Reconciling state hint",
    "platformControl.providers.loadedModelStateHintLoaded": "Loaded state hint",
    "platformControl.providers.loadPanelTimelineAccepted": "Request accepted",
    "platformControl.providers.loadPanelTimelineLoading": "Runtime loading model",
    "platformControl.providers.loadPanelTimelineReady": "Runtime ready",
    "platformControl.providers.loadPanelTimelineFailed": "Runtime failed",
    "platformControl.providers.loadPanelPhases.loading": "Loading",
    "platformControl.providers.loadPanelPhases.reconciling": "Reconciling",
    "platformControl.providers.loadPanelPhases.loaded": "Ready",
    "platformControl.providers.loadPanelPhases.error": "Failed",
    "platformControl.providers.loadPanelPhases.idle": "Idle",
  };

  if (key === "platformControl.providers.loadPanelSummaryLoading") {
    return `Loading ${String(options.name ?? "")}`;
  }
  if (key === "platformControl.providers.loadPanelSummaryReconciling") {
    return `Reconciling ${String(options.name ?? "")}`;
  }
  if (key === "platformControl.providers.loadPanelSummaryLoaded") {
    return `Loaded ${String(options.name ?? "")}`;
  }
  if (key === "platformControl.providers.loadPanelSummaryError") {
    return `Failed ${String(options.name ?? "")}`;
  }

  return dictionary[key] ?? key;
}

type HookHarnessProps = {
  provider: PlatformProvider | null;
  providerId: string;
  supportsLocalSlot: boolean;
  slotModelId: string;
  selectedSlotModel: ManagedModel | null;
  reload: () => Promise<void>;
};

function HookHarness(props: HookHarnessProps): JSX.Element {
  const {
    isLoadPanelOpen,
    loadPanelPhase,
    trackedLoad,
    dismissTrackedLoadPanel,
  } = usePlatformProviderLoadState(props);

  return (
    <div>
      <span data-testid="panel-open">{String(isLoadPanelOpen)}</span>
      <span data-testid="panel-phase">{loadPanelPhase}</span>
      <span data-testid="tracked-model">{trackedLoad?.requestedModelName ?? ""}</span>
      <button type="button" onClick={dismissTrackedLoadPanel}>
        dismiss
      </button>
    </div>
  );
}

describe("providerLoad", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.useRealTimers();
  });

  it("derives managed-model display text without a duplicate secondary line", () => {
    const display = buildProviderLoadDisplayData(
      buildProvider({
        loaded_managed_model_id: "model-1",
        loaded_managed_model_name: "Model One",
        load_state: "loaded",
      }),
      null,
      "loaded",
      translate,
    );

    expect(display.loadedModelPrimary).toBe("Model One");
    expect(display.loadedModelSecondaryDetail).toBeNull();
    expect(display.loadStateHelperText).toBe("Loaded state hint");
    expect(display.loadPanelSummary).toBe("Loaded Model One");
  });

  it("uses the runtime model as the primary assigned-model text when no managed model exists", () => {
    const display = buildProviderLoadDisplayData(
      buildProvider({
        loaded_runtime_model_id: "/models/embeddings/all-MiniLM-L6-v2",
        load_state: "loaded",
      }),
      null,
      "loaded",
      translate,
    );

    expect(display.loadedModelPrimary).toBe("/models/embeddings/all-MiniLM-L6-v2");
    expect(display.loadedModelSecondaryDetail).toBeNull();
    expect(display.loadPanelRuntimeLabel).toBe("/models/embeddings/all-MiniLM-L6-v2");
  });

  it("chooses state-specific helper text and preserves runtime errors", () => {
    const loadingDisplay = buildProviderLoadDisplayData(
      buildProvider({ load_state: "loading" }),
      null,
      "loading",
      translate,
    );
    const errorDisplay = buildProviderLoadDisplayData(
      buildProvider({ load_state: "error", load_error: "GPU out of memory" }),
      null,
      "error",
      translate,
    );

    expect(loadingDisplay.loadStateHelperText).toBe("Loading state hint");
    expect(errorDisplay.loadStateHelperText).toBe("GPU out of memory");
    expect(errorDisplay.hasLoadError).toBe(true);
  });
});

describe("usePlatformProviderLoadState", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("opens the panel and polls while the runtime is loading", async () => {
    vi.useFakeTimers();
    const reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const selectedSlotModel = buildLocalModel();

    render(
      <HookHarness
        provider={buildProvider({ load_state: "loading" })}
        providerId="provider-1"
        supportsLocalSlot
        slotModelId={selectedSlotModel.id}
        selectedSlotModel={selectedSlotModel}
        reload={reload}
      />,
    );

    expect(screen.getByTestId("panel-open")).toHaveTextContent("true");
    expect(screen.getByTestId("panel-phase")).toHaveTextContent("loading");
    expect(screen.getByTestId("tracked-model")).toHaveTextContent(selectedSlotModel.name);

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(reload).toHaveBeenCalledTimes(1);
  });
});
