import type { PlatformProvider } from "../../api/platform";

export type ProviderLoadPanelPhase = "idle" | "loading" | "reconciling" | "loaded" | "error";

export type StoredProviderLoadStatus = {
  providerId: string;
  requestedModelId: string;
  requestedModelName: string;
  statusOpen: boolean;
  dismissedTerminalState: boolean;
};

export type ProviderLoadTimelineItem = {
  label: string;
  state: "done" | "active" | "pending" | "error";
};

export type ProviderLoadDisplayData = {
  loadedModelPrimary: string;
  loadedModelSecondaryDetail: string | null;
  providerLoadState: string;
  loadStateHelperText: string;
  hasLoadError: boolean;
  loadPanelModelName: string;
  loadPanelModelId: string;
  loadPanelRuntimeLabel: string;
  loadPanelPhaseLabel: string;
  loadPanelSummary: string;
  loadTimelineItems: ProviderLoadTimelineItem[];
};

type Translate = (key: string, options?: Record<string, unknown>) => string;

export function normalizeProviderLoadPhase(value: string | null | undefined): ProviderLoadPanelPhase {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (
    normalized === "loading"
    || normalized === "reconciling"
    || normalized === "loaded"
    || normalized === "error"
  ) {
    return normalized;
  }
  return "idle";
}

export function isActiveProviderLoadPhase(phase: ProviderLoadPanelPhase): boolean {
  return phase === "loading" || phase === "reconciling";
}

export function isTerminalProviderLoadPhase(phase: ProviderLoadPanelPhase): boolean {
  return phase === "loaded" || phase === "error";
}

export function buildProviderLoadDisplayData(
  provider: PlatformProvider | null,
  trackedLoad: StoredProviderLoadStatus | null,
  loadPanelPhase: ProviderLoadPanelPhase,
  t: Translate,
): ProviderLoadDisplayData {
  const loadedModelPrimary = provider?.loaded_managed_model_name
    ?? provider?.loaded_managed_model_id
    ?? provider?.loaded_runtime_model_id
    ?? provider?.loaded_local_path
    ?? t("platformControl.summary.none");
  const loadedModelSecondaryDetailCandidate = provider?.loaded_runtime_model_id ?? provider?.loaded_local_path ?? null;
  const loadedModelSecondaryDetail = loadedModelSecondaryDetailCandidate && loadedModelSecondaryDetailCandidate !== loadedModelPrimary
    ? loadedModelSecondaryDetailCandidate
    : null;
  const providerLoadState = String(provider?.load_state ?? "empty").trim() || "empty";
  const loadStateHelperText = provider?.load_error
    ? provider.load_error
    : providerLoadState === "loaded"
      ? t("platformControl.providers.loadedModelStateHintLoaded")
      : providerLoadState === "reconciling"
        ? t("platformControl.providers.loadedModelStateHintReconciling")
        : providerLoadState === "loading"
          ? t("platformControl.providers.loadedModelStateHintLoading")
          : t("platformControl.providers.loadedModelStateHintEmpty");
  const loadPanelModelName = trackedLoad?.requestedModelName
    || provider?.loaded_managed_model_name
    || provider?.loaded_managed_model_id
    || t("platformControl.summary.none");
  const loadPanelModelId = trackedLoad?.requestedModelId
    || provider?.loaded_managed_model_id
    || t("platformControl.summary.none");
  const loadPanelRuntimeLabel = provider?.loaded_runtime_model_id ?? provider?.loaded_local_path ?? providerLoadState;
  const loadPanelPhaseLabel = t(`platformControl.providers.loadPanelPhases.${loadPanelPhase}`);
  const loadPanelSummary = loadPanelPhase === "loading"
    ? t("platformControl.providers.loadPanelSummaryLoading", { name: loadPanelModelName })
    : loadPanelPhase === "reconciling"
      ? t("platformControl.providers.loadPanelSummaryReconciling", { name: loadPanelModelName })
      : loadPanelPhase === "loaded"
        ? t("platformControl.providers.loadPanelSummaryLoaded", { name: loadPanelModelName })
        : loadPanelPhase === "error"
          ? t("platformControl.providers.loadPanelSummaryError", { name: loadPanelModelName })
          : "";
  const loadTimelineItems: ProviderLoadTimelineItem[] = [
    {
      label: t("platformControl.providers.loadPanelTimelineAccepted"),
      state: "done",
    },
    {
      label: t("platformControl.providers.loadPanelTimelineLoading"),
      state: loadPanelPhase === "loaded"
        ? "done"
        : loadPanelPhase === "error"
          ? "error"
          : isActiveProviderLoadPhase(loadPanelPhase)
            ? "active"
            : "pending",
    },
    {
      label: loadPanelPhase === "error"
        ? t("platformControl.providers.loadPanelTimelineFailed")
        : t("platformControl.providers.loadPanelTimelineReady"),
      state: loadPanelPhase === "loaded"
        ? "done"
        : loadPanelPhase === "error"
          ? "error"
          : "pending",
    },
  ];

  return {
    loadedModelPrimary,
    loadedModelSecondaryDetail,
    providerLoadState,
    loadStateHelperText,
    hasLoadError: Boolean(provider?.load_error),
    loadPanelModelName,
    loadPanelModelId,
    loadPanelRuntimeLabel,
    loadPanelPhaseLabel,
    loadPanelSummary,
    loadTimelineItems,
  };
}
