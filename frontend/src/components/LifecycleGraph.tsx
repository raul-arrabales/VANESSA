import { useId, useMemo, useRef } from "react";
import type { TFunction } from "i18next";
import ModalDialog from "./ModalDialog";

export type LifecycleStateDefinition = {
  id: string;
  label: string;
  description?: string;
  x?: number;
  y?: number;
};

export type LifecycleTransitionDefinition = {
  from: string;
  to: string;
  label?: string;
};

export type LifecycleGraphDefinition = {
  artifactType: string;
  states: LifecycleStateDefinition[];
  transitions: LifecycleTransitionDefinition[];
};

export type LifecycleCounts = {
  byState: Record<string, number>;
  unknown: number;
};

export type LifecycleHighlight = {
  currentState: string | null;
  outgoingTransitions: Set<string>;
};

export type LifecycleGraphProps = {
  definition: LifecycleGraphDefinition;
  counts?: LifecycleCounts;
  currentState?: string | null;
  supportingText?: string;
  currentLabel?: string;
  unknownLabel?: string;
};

export type LifecycleGraphModalProps = LifecycleGraphProps & {
  title: string;
  description?: string;
  closeLabel: string;
  onClose: () => void;
};

export type LifecycleGraphDefinitionOptions<StateId extends string = string> = {
  artifactType: string;
  stateIds: readonly StateId[];
  i18nBase: string;
  transitions: readonly LifecycleTransitionDefinition[];
  positions?: Partial<Record<StateId, { x: number; y: number }>> | readonly { x: number; y: number }[];
  transitionLabelKey?: (transition: LifecycleTransitionDefinition) => string;
};

export type LifecycleGraphPanelProps<T> = {
  title: string;
  description: string;
  definition: LifecycleGraphDefinition;
  items: T[];
  getState: (item: T) => string | null | undefined;
  currentLabel: string;
  unknownLabel: string;
  titleAs?: "h2" | "h3";
  className?: string;
  headerClassName?: string;
  headerContentClassName?: string;
};

export type LifecycleGraphActionModalProps<T> = Omit<LifecycleGraphModalProps, "title" | "currentState" | "supportingText" | "onClose"> & {
  item: T | null;
  getTitle: (item: T) => string;
  getCurrentState: (item: T) => string | null | undefined;
  getSupportingText: (item: T) => string;
  onClose: () => void;
};

function isPositionRecord<StateId extends string>(
  positions: LifecycleGraphDefinitionOptions<StateId>["positions"],
): positions is Partial<Record<StateId, { x: number; y: number }>> {
  return Boolean(positions) && !Array.isArray(positions);
}

function transitionId(transition: LifecycleTransitionDefinition): string {
  return `${transition.from}->${transition.to}`;
}

export function buildLifecycleGraphDefinition<StateId extends string>(
  t: TFunction<"common">,
  options: LifecycleGraphDefinitionOptions<StateId>,
): LifecycleGraphDefinition {
  return {
    artifactType: options.artifactType,
    states: options.stateIds.map((stateId, index) => {
      const position = Array.isArray(options.positions)
        ? options.positions[index]
        : isPositionRecord(options.positions)
          ? options.positions[stateId]
          : undefined;
      return {
        id: stateId,
        label: t(`${options.i18nBase}.states.${stateId}`),
        ...position,
      };
    }),
    transitions: options.transitions.map((transition) => ({
      ...transition,
      label: t(options.transitionLabelKey?.(transition) ?? `${options.i18nBase}.transitions.${transition.from}.${transition.to}`),
    })),
  };
}

function truncateLifecycleLabelLine(line: string, maxLineLength: number): string {
  if (line.length <= maxLineLength) {
    return line;
  }
  if (maxLineLength <= 3) {
    return line.slice(0, maxLineLength);
  }
  return `${line.slice(0, maxLineLength - 3)}...`;
}

export function getLifecycleNodeLabelLines(label: string, maxLineLength = 16, maxLines = 2): string[] {
  const normalizedLabel = label.trim().replace(/\s+/g, " ");
  if (!normalizedLabel) {
    return [""];
  }

  const words = normalizedLabel.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    const nextLine = currentLine ? `${currentLine} ${word}` : word;
    if (nextLine.length <= maxLineLength) {
      currentLine = nextLine;
      continue;
    }
    if (currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      lines.push(truncateLifecycleLabelLine(word, maxLineLength));
      currentLine = "";
    }
  }

  if (currentLine) {
    lines.push(currentLine);
  }

  if (lines.length <= maxLines) {
    return lines.map((line) => truncateLifecycleLabelLine(line, maxLineLength));
  }

  const visibleLines = lines.slice(0, maxLines);
  visibleLines[maxLines - 1] = truncateLifecycleLabelLine(lines.slice(maxLines - 1).join(" "), maxLineLength);
  return visibleLines;
}

function statePosition(state: LifecycleStateDefinition, index: number, total: number): { x: number; y: number } {
  if (typeof state.x === "number" && typeof state.y === "number") {
    return { x: state.x, y: state.y };
  }
  const columns = Math.min(Math.max(total, 1), 4);
  const column = index % columns;
  const row = Math.floor(index / columns);
  return {
    x: 90 + column * 180,
    y: 78 + row * 120,
  };
}

export function deriveLifecycleCounts<T>(
  items: T[],
  definition: LifecycleGraphDefinition,
  getState: (item: T) => string | null | undefined,
): LifecycleCounts {
  const knownStates = new Set(definition.states.map((state) => state.id));
  const byState = Object.fromEntries(definition.states.map((state) => [state.id, 0]));
  let unknown = 0;

  for (const item of items) {
    const state = String(getState(item) ?? "").trim().toLowerCase();
    if (knownStates.has(state)) {
      byState[state] += 1;
    } else {
      unknown += 1;
    }
  }

  return { byState, unknown };
}

export function resolveLifecycleHighlight<T>(
  item: T,
  definition: LifecycleGraphDefinition,
  getState: (item: T) => string | null | undefined,
): LifecycleHighlight {
  const currentState = String(getState(item) ?? "").trim().toLowerCase() || null;
  const knownStates = new Set(definition.states.map((state) => state.id));
  const resolvedCurrentState = currentState && knownStates.has(currentState) ? currentState : null;
  return {
    currentState: resolvedCurrentState,
    outgoingTransitions: new Set(
      definition.transitions
        .filter((transition) => transition.from === resolvedCurrentState)
        .map(transitionId),
    ),
  };
}

export function LifecycleGraph({
  definition,
  counts,
  currentState,
  supportingText,
  currentLabel = "Current",
  unknownLabel = "Unknown",
}: LifecycleGraphProps): JSX.Element {
  const markerId = useId().replace(/:/g, "");
  const arrowMarkerId = `lifecycle-arrow-${definition.artifactType}-${markerId}`;
  const availableArrowMarkerId = `${arrowMarkerId}-available`;
  const highlight = useMemo(
    () => resolveLifecycleHighlight({ state: currentState }, definition, (item) => item.state),
    [currentState, definition],
  );
  const positions = useMemo(
    () => new Map(definition.states.map((state, index) => [state.id, statePosition(state, index, definition.states.length)])),
    [definition.states],
  );

  return (
    <div className="lifecycle-graph">
      <svg className="lifecycle-graph-svg" viewBox="0 0 760 300" role="img" aria-label={`${definition.artifactType} lifecycle graph`}>
        <defs>
          <marker id={arrowMarkerId} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path className="lifecycle-graph-arrow" d="M 0 0 L 10 5 L 0 10 z" />
          </marker>
          <marker id={availableArrowMarkerId} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path className="lifecycle-graph-arrow-available" d="M 0 0 L 10 5 L 0 10 z" />
          </marker>
        </defs>
        {definition.transitions.map((transition) => {
          const start = positions.get(transition.from);
          const end = positions.get(transition.to);
          if (!start || !end) {
            return null;
          }
          const isAvailable = highlight.outgoingTransitions.has(transitionId(transition));
          const isSelfColumn = start.x === end.x;
          const path = isSelfColumn
            ? `M ${start.x + 72} ${start.y + 26} C ${start.x + 142} ${start.y + 34}, ${end.x + 142} ${end.y - 34}, ${end.x + 72} ${end.y - 26}`
            : `M ${start.x + 72} ${start.y} L ${end.x - 72} ${end.y}`;
          return (
            <path
              key={transitionId(transition)}
              className="lifecycle-graph-edge"
              data-available={isAvailable ? "true" : undefined}
              d={path}
              markerEnd={`url(#${isAvailable ? availableArrowMarkerId : arrowMarkerId})`}
            >
              {transition.label ? <title>{transition.label}</title> : null}
            </path>
          );
        })}
        {definition.states.map((state, index) => {
          const position = positions.get(state.id) ?? statePosition(state, index, definition.states.length);
          const isCurrent = highlight.currentState === state.id;
          const count = counts?.byState[state.id] ?? null;
          const labelLines = getLifecycleNodeLabelLines(state.label);
          const labelStartY = labelLines.length === 1 ? 24 : 17;
          return (
            <g
              key={state.id}
              className="lifecycle-graph-node"
              data-current={isCurrent ? "true" : undefined}
              transform={`translate(${position.x - 70} ${position.y - 28})`}
            >
              <title>{state.label}</title>
              <rect width="140" height="56" rx="8" />
              <text x="70" y={labelStartY} textAnchor="middle">
                {labelLines.map((line, lineIndex) => (
                  <tspan key={`${state.id}-${lineIndex}`} x="70" dy={lineIndex === 0 ? 0 : 13}>{line}</tspan>
                ))}
              </text>
              {count !== null ? <text className="lifecycle-graph-node-count" x="70" y="46" textAnchor="middle">{count}</text> : null}
            </g>
          );
        })}
      </svg>
      {supportingText ? <p className="status-text lifecycle-graph-supporting-text">{supportingText}</p> : null}
      <div className="lifecycle-graph-fallback" aria-label={`${definition.artifactType} lifecycle states`}>
        {definition.states.map((state) => (
          <div key={state.id} className="lifecycle-graph-fallback-row" data-current={highlight.currentState === state.id ? "true" : undefined}>
            <span className="field-label">{state.label}</span>
            {counts ? <span className="status-text">{counts.byState[state.id]}</span> : null}
            {highlight.currentState === state.id ? <span className="platform-badge" data-tone="active">{currentLabel}</span> : null}
          </div>
        ))}
        {counts && counts.unknown > 0 ? (
          <div className="lifecycle-graph-fallback-row">
            <span className="field-label">{unknownLabel}</span>
            <span className="status-text">{counts.unknown}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function LifecycleGraphPanel<T>({
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

export function LifecycleGraphModal({
  title,
  description,
  closeLabel,
  onClose,
  ...graphProps
}: LifecycleGraphModalProps): JSX.Element {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <ModalDialog
      className="lifecycle-graph-modal"
      title={title}
      description={description}
      onClose={onClose}
      initialFocusRef={closeButtonRef}
      actions={(
        <button ref={closeButtonRef} type="button" className="btn btn-primary" onClick={onClose}>
          {closeLabel}
        </button>
      )}
    >
      <LifecycleGraph {...graphProps} />
    </ModalDialog>
  );
}

export function LifecycleGraphActionModal<T>({
  item,
  getTitle,
  getCurrentState,
  getSupportingText,
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
      supportingText={getSupportingText(item)}
    />
  );
}
