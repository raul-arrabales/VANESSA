import { useEffect, useMemo, useState } from "react";
import type { PlaygroundVariant } from "../types";

const STORAGE_PREFIX = "vanessa.playgrounds";

function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") {
    return fallback;
  }
  const stored = window.localStorage.getItem(key);
  if (stored === "true") {
    return true;
  }
  if (stored === "false") {
    return false;
  }
  return fallback;
}

function readStoredString(key: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }
  return window.localStorage.getItem(key) ?? fallback;
}

export function usePlaygroundPreferences(playgroundKind: PlaygroundVariant) {
  const storageKeys = useMemo(() => ({
    draft: `${STORAGE_PREFIX}.${playgroundKind}.draft`,
    sidebarCollapsed: `${STORAGE_PREFIX}.${playgroundKind}.sidebarCollapsed`,
  }), [playgroundKind]);

  const [draft, setDraft] = useState(() => readStoredString(storageKeys.draft, ""));
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => readStoredBoolean(storageKeys.sidebarCollapsed, false));

  useEffect(() => {
    window.localStorage.setItem(storageKeys.draft, draft);
  }, [draft, storageKeys.draft]);

  useEffect(() => {
    window.localStorage.setItem(storageKeys.sidebarCollapsed, String(isSidebarCollapsed));
  }, [isSidebarCollapsed, storageKeys.sidebarCollapsed]);

  return {
    draft,
    setDraft,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
    toggleSidebar: (): void => setIsSidebarCollapsed((current) => !current),
  };
}
