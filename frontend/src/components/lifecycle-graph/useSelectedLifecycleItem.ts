import { useCallback, useState } from "react";

export type SelectedLifecycleItemState<T> = {
  selectedLifecycleItem: T | null;
  openLifecycleItem: (item: T) => void;
  closeLifecycleItem: () => void;
};

export function useSelectedLifecycleItem<T>(): SelectedLifecycleItemState<T> {
  const [selectedLifecycleItem, setSelectedLifecycleItem] = useState<T | null>(null);
  const openLifecycleItem = useCallback((item: T) => setSelectedLifecycleItem(item), []);
  const closeLifecycleItem = useCallback(() => setSelectedLifecycleItem(null), []);

  return {
    selectedLifecycleItem,
    openLifecycleItem,
    closeLifecycleItem,
  };
}
