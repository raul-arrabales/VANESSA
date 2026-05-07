import { useEffect, useState } from "react";
import type { PlaygroundRunStatus } from "../types";

type AssistantStatusTimelineProps = {
  statuses: PlaygroundRunStatus[];
  messageId: string;
  responseText?: string;
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

function timestampMillis(value?: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function totalDurationMs(statuses: PlaygroundRunStatus[]): number | null {
  const startedAt = statuses
    .map((status) => timestampMillis(status.started_at))
    .filter((value): value is number => value !== null);
  const completedAt = statuses
    .map((status) => timestampMillis(status.completed_at))
    .filter((value): value is number => value !== null);
  if (startedAt.length > 0 && completedAt.length > 0) {
    const duration = Math.max(...completedAt) - Math.min(...startedAt);
    return duration >= 0 ? duration : null;
  }

  const durationTotal = statuses.reduce((total, status) => (
    typeof status.duration_ms === "number" && Number.isFinite(status.duration_ms) && status.duration_ms > 0
      ? total + status.duration_ms
      : total
  ), 0);
  return durationTotal > 0 ? durationTotal : null;
}

function generationDurationMs(statuses: PlaygroundRunStatus[]): number | null {
  const generationStatuses = statuses.filter((status) => status.kind === "generating");
  return totalDurationMs(generationStatuses.length > 0 ? generationStatuses : statuses);
}

function estimateTokenCount(text?: string): number {
  const normalized = (text ?? "").trim();
  if (!normalized) {
    return 0;
  }
  return Math.max(1, Math.round(normalized.length / 4));
}

function formatTokensPerSecond(responseText: string | undefined, durationMs: number | null): string {
  const tokenCount = estimateTokenCount(responseText);
  if (!durationMs || durationMs <= 0 || tokenCount === 0) {
    return "";
  }
  const tokensPerSecond = tokenCount / (durationMs / 1000);
  if (!Number.isFinite(tokensPerSecond) || tokensPerSecond <= 0) {
    return "";
  }
  return `~${tokensPerSecond.toFixed(tokensPerSecond < 10 ? 1 : 0)} tok/s`;
}

function generationSummaryLabel(statuses: PlaygroundRunStatus[], responseText?: string): string {
  const duration = formatDuration(totalDurationMs(statuses));
  const throughput = formatTokensPerSecond(responseText, generationDurationMs(statuses));
  const metrics = [duration, throughput].filter(Boolean).join(", ");
  return metrics ? `Generation (${metrics})` : "Generation";
}

export default function AssistantStatusTimeline({
  statuses,
  messageId,
  responseText,
}: AssistantStatusTimelineProps): JSX.Element | null {
  const hasRunningStatus = statuses.some((status) => status.state === "running");
  const [isGroupOpen, setIsGroupOpen] = useState(false);

  useEffect(() => {
    if (!hasRunningStatus) {
      setIsGroupOpen(false);
    }
  }, [hasRunningStatus, messageId]);

  if (statuses.length === 0) {
    return null;
  }

  const timeline = (
    <div className="assistant-status-timeline-list">
      {statuses.map((status) => (
        <AssistantStatusItem key={status.id} status={status} messageId={messageId} />
      ))}
    </div>
  );

  if (hasRunningStatus) {
    return (
      <div className="assistant-status-timeline" aria-label="Response progress">
        {timeline}
      </div>
    );
  }

  return (
    <div className="assistant-status-timeline" aria-label="Response progress">
      <details className="assistant-status-group" open={isGroupOpen}>
        <summary
          className="assistant-status-group-summary"
          aria-expanded={isGroupOpen}
          onClick={(event) => {
            event.preventDefault();
            setIsGroupOpen((current) => !current);
          }}
        >
          <span className="assistant-status-group-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16" focusable="false">
              <path d="M6 4.25 9.75 8 6 11.75" />
            </svg>
          </span>
          <span>{generationSummaryLabel(statuses, responseText)}</span>
        </summary>
        {timeline}
      </details>
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
