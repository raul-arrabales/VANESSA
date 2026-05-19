import { useId, useMemo } from "react";
import { lifecycleTransitionId, resolveLifecycleHighlight } from "./definition";
import { getLifecycleNodeLabelLines, getLifecycleStatePosition } from "./layout";
import type { LifecycleGraphProps, LifecycleSummaryRow } from "./types";

function LifecycleSummaryRows({ rows }: { rows: LifecycleSummaryRow[] }): JSX.Element {
  return (
    <dl className="lifecycle-graph-summary">
      {rows.map((row) => (
        <div key={`${row.label}-${row.value}`} className="lifecycle-graph-summary-row">
          <dt className="field-label">{row.label}</dt>
          <dd>
            <span className="platform-badge" data-tone={row.tone}>
              {row.value}
            </span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function LifecycleGraph({
  definition,
  counts,
  currentState,
  supportingText,
  summaryRows,
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
    () => new Map(definition.states.map((state, index) => [state.id, getLifecycleStatePosition(state, index, definition.states.length)])),
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
          const isAvailable = highlight.outgoingTransitions.has(lifecycleTransitionId(transition));
          const isSelfColumn = start.x === end.x;
          const path = isSelfColumn
            ? `M ${start.x + 72} ${start.y + 26} C ${start.x + 142} ${start.y + 34}, ${end.x + 142} ${end.y - 34}, ${end.x + 72} ${end.y - 26}`
            : `M ${start.x + 72} ${start.y} L ${end.x - 72} ${end.y}`;
          return (
            <path
              key={lifecycleTransitionId(transition)}
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
          const position = positions.get(state.id) ?? getLifecycleStatePosition(state, index, definition.states.length);
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
      {summaryRows?.length ? <LifecycleSummaryRows rows={summaryRows} /> : null}
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
