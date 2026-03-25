import { useEffect, useState } from "react";
import type { ManagedModel } from "../../../api/modelops/types";
import type { PlatformProvider } from "../../../api/platform";
import {
  type ProviderLoadPanelPhase,
  type StoredProviderLoadStatus,
  isActiveProviderLoadPhase,
  isTerminalProviderLoadPhase,
  normalizeProviderLoadPhase,
} from "../providerLoad";

type UsePlatformProviderLoadStateParams = {
  provider: PlatformProvider | null;
  providerId: string;
  supportsLocalSlot: boolean;
  slotModelId: string;
  selectedSlotModel: ManagedModel | null;
  reload: () => Promise<void>;
};

type UsePlatformProviderLoadStateResult = {
  isLoadPanelOpen: boolean;
  loadPanelPhase: ProviderLoadPanelPhase;
  trackedLoad: StoredProviderLoadStatus | null;
  persistTrackedLoad: (nextTrackedLoad: StoredProviderLoadStatus) => void;
  dismissTrackedLoadPanel: () => void;
  resetTrackedLoadState: () => void;
};

const PROVIDER_LOAD_STATUS_STORAGE_PREFIX = "vanessa:platform-provider-load:";

function providerLoadStatusStorageKey(providerId: string): string {
  return `${PROVIDER_LOAD_STATUS_STORAGE_PREFIX}${providerId}`;
}

function readStoredProviderLoadStatus(providerId: string): StoredProviderLoadStatus | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const rawValue = window.sessionStorage.getItem(providerLoadStatusStorageKey(providerId));
    if (!rawValue) {
      return null;
    }
    const parsed = JSON.parse(rawValue) as Partial<StoredProviderLoadStatus>;
    if (parsed.providerId !== providerId) {
      return null;
    }
    return {
      providerId,
      requestedModelId: String(parsed.requestedModelId ?? ""),
      requestedModelName: String(parsed.requestedModelName ?? ""),
      statusOpen: Boolean(parsed.statusOpen),
      dismissedTerminalState: Boolean(parsed.dismissedTerminalState),
    };
  } catch {
    return null;
  }
}

function writeStoredProviderLoadStatus(payload: StoredProviderLoadStatus): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(
    providerLoadStatusStorageKey(payload.providerId),
    JSON.stringify(payload),
  );
}

function clearStoredProviderLoadStatus(providerId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(providerLoadStatusStorageKey(providerId));
}

function sameStoredProviderLoadStatus(
  left: StoredProviderLoadStatus | null,
  right: StoredProviderLoadStatus | null,
): boolean {
  if (left === right) {
    return true;
  }
  if (!left || !right) {
    return false;
  }
  return (
    left.providerId === right.providerId
    && left.requestedModelId === right.requestedModelId
    && left.requestedModelName === right.requestedModelName
    && left.statusOpen === right.statusOpen
    && left.dismissedTerminalState === right.dismissedTerminalState
  );
}

export function usePlatformProviderLoadState({
  provider,
  providerId,
  supportsLocalSlot,
  slotModelId,
  selectedSlotModel,
  reload,
}: UsePlatformProviderLoadStateParams): UsePlatformProviderLoadStateResult {
  const [isLoadPanelOpen, setIsLoadPanelOpen] = useState(false);
  const [loadPanelPhase, setLoadPanelPhase] = useState<ProviderLoadPanelPhase>("idle");
  const [trackedLoad, setTrackedLoad] = useState<StoredProviderLoadStatus | null>(null);

  useEffect(() => {
    if (!supportsLocalSlot || !provider) {
      return;
    }
    const backendPhase = normalizeProviderLoadPhase(provider.load_state);
    if (!isActiveProviderLoadPhase(backendPhase)) {
      return;
    }
    const timer = window.setTimeout(() => {
      void reload();
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [provider, reload, supportsLocalSlot]);

  useEffect(() => {
    if (!supportsLocalSlot || !providerId) {
      setTrackedLoad(null);
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
      return;
    }
    setTrackedLoad(readStoredProviderLoadStatus(providerId));
  }, [providerId, supportsLocalSlot]);

  useEffect(() => {
    if (!supportsLocalSlot || !provider) {
      return;
    }

    const backendPhase = normalizeProviderLoadPhase(provider.load_state);
    const providerModelId = provider.loaded_managed_model_id ?? "";
    const providerModelName = provider.loaded_managed_model_name ?? providerModelId;
    let nextTrackedLoad = trackedLoad;

    if (isActiveProviderLoadPhase(backendPhase)) {
      const candidate: StoredProviderLoadStatus = {
        providerId: provider.id,
        requestedModelId: providerModelId || trackedLoad?.requestedModelId || slotModelId,
        requestedModelName: providerModelName || trackedLoad?.requestedModelName || selectedSlotModel?.name || slotModelId,
        statusOpen: true,
        dismissedTerminalState: false,
      };
      if (!sameStoredProviderLoadStatus(trackedLoad, candidate)) {
        setTrackedLoad(candidate);
        writeStoredProviderLoadStatus(candidate);
        nextTrackedLoad = candidate;
      }
      setLoadPanelPhase(backendPhase);
      setIsLoadPanelOpen(true);
      return;
    }

    if (isTerminalProviderLoadPhase(backendPhase)) {
      setLoadPanelPhase(backendPhase);
      if (nextTrackedLoad && nextTrackedLoad.statusOpen && !nextTrackedLoad.dismissedTerminalState) {
        const candidate: StoredProviderLoadStatus = {
          ...nextTrackedLoad,
          requestedModelId: nextTrackedLoad.requestedModelId || providerModelId,
          requestedModelName: nextTrackedLoad.requestedModelName || providerModelName,
        };
        if (!sameStoredProviderLoadStatus(nextTrackedLoad, candidate)) {
          setTrackedLoad(candidate);
          writeStoredProviderLoadStatus(candidate);
        }
        setIsLoadPanelOpen(true);
      }
      return;
    }

    if (!nextTrackedLoad || nextTrackedLoad.dismissedTerminalState || !nextTrackedLoad.statusOpen) {
      setIsLoadPanelOpen(false);
      setLoadPanelPhase("idle");
    }
  }, [provider, selectedSlotModel, slotModelId, supportsLocalSlot, trackedLoad]);

  function persistTrackedLoad(nextTrackedLoad: StoredProviderLoadStatus): void {
    setTrackedLoad(nextTrackedLoad);
    writeStoredProviderLoadStatus(nextTrackedLoad);
    setLoadPanelPhase("loading");
    setIsLoadPanelOpen(true);
  }

  function dismissTrackedLoadPanel(): void {
    if (!providerId || !trackedLoad) {
      setIsLoadPanelOpen(false);
      return;
    }
    const dismissedStatus: StoredProviderLoadStatus = {
      ...trackedLoad,
      statusOpen: false,
      dismissedTerminalState: true,
    };
    setTrackedLoad(dismissedStatus);
    writeStoredProviderLoadStatus(dismissedStatus);
    setIsLoadPanelOpen(false);
  }

  function resetTrackedLoadState(): void {
    if (providerId) {
      clearStoredProviderLoadStatus(providerId);
    }
    setTrackedLoad(null);
    setIsLoadPanelOpen(false);
    setLoadPanelPhase("idle");
  }

  return {
    isLoadPanelOpen,
    loadPanelPhase,
    trackedLoad,
    persistTrackedLoad,
    dismissTrackedLoadPanel,
    resetTrackedLoadState,
  };
}
