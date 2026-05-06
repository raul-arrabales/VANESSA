import { useState } from "react";
import type { PlaygroundRunStatus } from "../types";

type AssistantStatusTimelineProps = {
  statuses: PlaygroundRunStatus[];
  messageId: string;
};

function formatDuration(durationMs?: number | null): string {
  if (typeof durationMs !== "number" || !Number.isFinite(durationMs) || durationMs < 0) {
    return "";
  }
  if (durationMs < 1000) {
    return `${Math.max(Math.round(durationMs), 1)}ms`;
  }
  return `${(durationMs / 1000).toFixed(durationMs < 10_000 ? 1 : 0)}s`;
}

function detailText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function statusLabel(status: PlaygroundRunStatus): string {
  const duration = formatDuration(status.duration_ms);
  return duration && status.state !== "running" ? `${status.label} - ${duration}` : status.label;
}

export default function AssistantStatusTimeline({
  statuses,
  messageId,
}: AssistantStatusTimelineProps): JSX.Element | null {
  if (statuses.length === 0) {
    return null;
  }

  return (
    <div className="assistant-status-timeline" aria-label="Response progress">
      {statuses.map((status) => (
        <AssistantStatusItem key={status.id} status={status} messageId={messageId} />
      ))}
    </div>
  );
}

function AssistantStatusItem({
  status,
  messageId,
}: {
  status: PlaygroundRunStatus;
  messageId: string;
}): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const details = status.details && typeof status.details === "object" ? status.details : {};
  const detailEntries = Object.entries(details)
    .map(([key, value]) => [key, detailText(value)] as const)
    .filter(([, value]) => value.length > 0);
  const detailsId = `assistant-status-${messageId}-${status.id}`;
  return (
    <details
      className="assistant-status-item"
      data-state={status.state}
      open={isOpen}
    >
      <summary
        className="assistant-status-summary"
        aria-controls={detailsId}
        aria-expanded={isOpen}
        onClick={(event) => {
          event.preventDefault();
          setIsOpen((current) => !current);
        }}
      >
        <span className="assistant-status-dot" aria-hidden="true" />
        <span className="assistant-status-label">{statusLabel(status)}</span>
        {status.summary ? <span className="assistant-status-extra">{status.summary}</span> : null}
      </summary>
      {detailEntries.length > 0 ? (
        <dl id={detailsId} className="assistant-status-details">
          {detailEntries.map(([key, value]) => (
            <div key={key} className="assistant-status-detail-row">
              <dt>{key.replace(/_/g, " ")}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </details>
  );
}
