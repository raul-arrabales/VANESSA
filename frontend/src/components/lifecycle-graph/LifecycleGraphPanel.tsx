import { useMemo } from "react";
import { deriveLifecycleCounts } from "./definition";
import LifecycleGraph from "./LifecycleGraph";
import type { LifecycleGraphPanelProps } from "./types";

export default function LifecycleGraphPanel<T>({
  title,
  description,
  definition,
  items,
  getState,
  currentLabel,
  unknownLabel,
  titleAs = "h3",
  className = "panel card-stack",
  headerClassName = "status-row",
  headerContentClassName,
}: LifecycleGraphPanelProps<T>): JSX.Element {
  const Heading = titleAs;
  const counts = useMemo(
    () => deriveLifecycleCounts(items, definition, getState),
    [definition, getState, items],
  );
  const headerContent = (
    <>
      <Heading className="section-title">{title}</Heading>
      <p className="status-text">{description}</p>
    </>
  );

  return (
    <article className={className}>
      <div className={headerClassName}>
        {headerContentClassName ? <div className={headerContentClassName}>{headerContent}</div> : headerContent}
      </div>
      <LifecycleGraph
        definition={definition}
        counts={counts}
        currentLabel={currentLabel}
        unknownLabel={unknownLabel}
      />
    </article>
  );
}
