import { LifecycleGraphModal } from "./LifecycleGraphModal";
import type { LifecycleGraphActionModalProps } from "./types";

export default function LifecycleGraphActionModal<T>({
  item,
  getTitle,
  getCurrentState,
  getSupportingText,
  getSummaryRows,
  ...modalProps
}: LifecycleGraphActionModalProps<T>): JSX.Element | null {
  if (!item) {
    return null;
  }

  return (
    <LifecycleGraphModal
      {...modalProps}
      title={getTitle(item)}
      currentState={getCurrentState(item)}
      supportingText={getSupportingText?.(item)}
      summaryRows={getSummaryRows?.(item)}
    />
  );
}
