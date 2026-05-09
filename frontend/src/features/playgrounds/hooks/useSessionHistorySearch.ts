import { useEffect, useState } from "react";
import type { PlaygroundSessionFilters } from "../types";

type UseSessionHistorySearchParams = {
  isSidebarCollapsed: boolean;
  onExpandSidebar: () => void;
};

type UseSessionHistorySearchResult = {
  isSearchOpen: boolean;
  searchFilters: PlaygroundSessionFilters;
  debouncedSearchFilters: PlaygroundSessionFilters;
  isSearchActive: boolean;
  setSearchFilters: (filters: PlaygroundSessionFilters) => void;
  clearSearch: () => void;
  toggleSearch: () => void;
};

function filtersAreEqual(left: PlaygroundSessionFilters, right: PlaygroundSessionFilters): boolean {
  return left.titleQuery === right.titleQuery
    && left.updatedFrom === right.updatedFrom
    && left.updatedTo === right.updatedTo;
}

function filtersAreActive(filters: PlaygroundSessionFilters): boolean {
  return Boolean(filters.titleQuery || filters.updatedFrom || filters.updatedTo);
}

export function useSessionHistorySearch({
  isSidebarCollapsed,
  onExpandSidebar,
}: UseSessionHistorySearchParams): UseSessionHistorySearchResult {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchFilters, setSearchFilters] = useState<PlaygroundSessionFilters>({});
  const [debouncedSearchFilters, setDebouncedSearchFilters] = useState<PlaygroundSessionFilters>({});

  useEffect(() => {
    if (filtersAreEqual(debouncedSearchFilters, searchFilters)) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearchFilters(searchFilters);
    }, 300);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [debouncedSearchFilters, searchFilters]);

  function toggleSearch(): void {
    if (isSidebarCollapsed) {
      onExpandSidebar();
      setIsSearchOpen(true);
      return;
    }
    setIsSearchOpen((current) => !current);
  }

  return {
    isSearchOpen,
    searchFilters,
    debouncedSearchFilters,
    isSearchActive: filtersAreActive(searchFilters),
    setSearchFilters,
    clearSearch: () => setSearchFilters({}),
    toggleSearch,
  };
}
