import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

type UseSessionSidebarMenuParams = {
  isCollapsed: boolean;
  isInteractionLocked: boolean;
  activeSessionId: string | null;
};

type UseSessionSidebarMenuResult = {
  sidebarRef: RefObject<HTMLElement>;
  openMenuSessionId: string | null;
  isMenuOpen: (sessionId: string) => boolean;
  toggleMenu: (sessionId: string) => void;
  closeMenu: () => void;
};

export function useSessionSidebarMenu({
  isCollapsed,
  isInteractionLocked,
  activeSessionId,
}: UseSessionSidebarMenuParams): UseSessionSidebarMenuResult {
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (isCollapsed || isInteractionLocked) {
      setOpenMenuSessionId(null);
    }
  }, [isCollapsed, isInteractionLocked]);

  useEffect(() => {
    setOpenMenuSessionId(null);
  }, [activeSessionId]);

  useEffect(() => {
    if (!openMenuSessionId) {
      return;
    }

    const handlePointerDown = (event: MouseEvent): void => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        setOpenMenuSessionId(null);
      }
    };

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpenMenuSessionId(null);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openMenuSessionId]);

  return {
    sidebarRef,
    openMenuSessionId,
    isMenuOpen: (sessionId: string) => openMenuSessionId === sessionId,
    toggleMenu: (sessionId: string) => {
      setOpenMenuSessionId((current) => (current === sessionId ? null : sessionId));
    },
    closeMenu: () => {
      setOpenMenuSessionId(null);
    },
  };
}
