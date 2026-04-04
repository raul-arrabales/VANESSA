import { useEffect, useState } from "react";

const SIDEBAR_COLLAPSED_STORAGE_KEY = "vanessa.sidebar.collapsed";

export function useAppShellState(pathname: string): {
  isMenuOpen: boolean;
  isSidebarDrawerOpen: boolean;
  isSidebarCollapsed: boolean;
  pendingRuntimeMode: "offline" | "online" | null;
  openUserMenu: () => void;
  closeUserMenu: () => void;
  toggleUserMenu: () => void;
  openSidebarDrawer: () => void;
  closeSidebarDrawer: () => void;
  toggleSidebarDrawer: () => void;
  toggleSidebarCollapsed: () => void;
  requestRuntimeMode: (nextMode: "offline" | "online") => void;
  cancelRuntimeMode: () => void;
  clearPendingRuntimeMode: () => void;
} {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSidebarDrawerOpen, setIsSidebarDrawerOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "true";
  });
  const [pendingRuntimeMode, setPendingRuntimeMode] = useState<"offline" | "online" | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  useEffect(() => {
    setIsMenuOpen(false);
    setIsSidebarDrawerOpen(false);
  }, [pathname]);

  return {
    isMenuOpen,
    isSidebarDrawerOpen,
    isSidebarCollapsed,
    pendingRuntimeMode,
    openUserMenu: () => setIsMenuOpen(true),
    closeUserMenu: () => setIsMenuOpen(false),
    toggleUserMenu: () => setIsMenuOpen((currentState) => !currentState),
    openSidebarDrawer: () => setIsSidebarDrawerOpen(true),
    closeSidebarDrawer: () => setIsSidebarDrawerOpen(false),
    toggleSidebarDrawer: () => setIsSidebarDrawerOpen((currentState) => !currentState),
    toggleSidebarCollapsed: () => setIsSidebarCollapsed((currentState) => !currentState),
    requestRuntimeMode: (nextMode) => setPendingRuntimeMode(nextMode),
    cancelRuntimeMode: () => setPendingRuntimeMode(null),
    clearPendingRuntimeMode: () => setPendingRuntimeMode(null),
  };
}
