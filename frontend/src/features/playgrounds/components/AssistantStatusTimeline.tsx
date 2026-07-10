import { useEffect, useState } from "react";
import type { PlaygroundRunStatus } from "../types";

type AssistantStatusTimelineProps = {
  statuses: PlaygroundRunStatus[];
  messageId: string;
  responseText?: string;
  isLive?: boolean;
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

function debugText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function copyToClipboard(text: string): void {
  if (!text || typeof navigator === "undefined" || !navigator.clipboard) {
    return;
  }
  void navigator.clipboard.writeText(text);
}

function llmMessagesText(messages: unknown): string {
  if (!Array.isArray(messages)) {
    return "";
  }
  return messages
    .map((message) => {
      if (!message || typeof message !== "object") {
        return "";
      }
      const raw = message as Record<string, unknown>;
      const role = String(raw.role ?? "message");
      const text = String(raw.text ?? "");
      return `${role.toUpperCase()}\n${text}`;
    })
    .filter(Boolean)
    .join("\n\n");
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
  isLive = false,
}: AssistantStatusTimelineProps): JSX.Element | null {
  const hasRunningStatus = isLive && statuses.some((status) => status.state === "running");
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
  const llmDebug = details.llm_debug && typeof details.llm_debug === "object"
    ? details.llm_debug as Record<string, unknown>
    : null;
  const detailEntries = Object.entries(details)
    .filter(([key]) => key !== "llm_debug")
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
      {llmDebug ? <AssistantLlmDebugDetails debug={llmDebug} /> : null}
    </details>
  );
}

function AssistantLlmDebugDetails({ debug }: { debug: Record<string, unknown> }): JSX.Element {
  const messagesText = llmMessagesText(debug.messages);
  const rawResponseText = debugText(debug.raw_response_text);
  const metaEntries = [
    ["call", debug.call_label ?? debug.call_id],
    ["agent", debug.agent_id ?? debug.assistant_ref],
    ["model", debug.requested_model],
    ["provider", debug.provider_slug ?? debug.provider_key],
    ["deployment", debug.deployment_profile_slug],
    ["status", debug.status_code],
  ]
    .map(([key, value]) => [key, detailText(value)] as const)
    .filter(([, value]) => value.length > 0);
  const extraEntries = [
    ["tools", debug.tools],
    ["tool calls", debug.tool_calls],
    ["parsed json", debug.parsed_json],
  ]
    .map(([key, value]) => [key, debugText(value)] as const)
    .filter(([, value]) => value.length > 0);

  return (
    <div className="assistant-status-llm-debug">
      {metaEntries.length > 0 ? (
        <dl className="assistant-status-debug-meta">
          {metaEntries.map(([key, value]) => (
            <div key={key} className="assistant-status-detail-row">
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {messagesText ? (
        <DebugBlock title="Messages sent to LLM" text={messagesText} />
      ) : null}
      {rawResponseText ? (
        <DebugBlock title="Raw model reply" text={rawResponseText} />
      ) : null}
      {extraEntries.map(([key, value]) => (
        <DebugBlock key={key} title={key} text={value} />
      ))}
    </div>
  );
}

function DebugBlock({ title, text }: { title: string; text: string }): JSX.Element {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return undefined;
    }
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  return (
    <section className="assistant-status-debug-block">
      <div className="assistant-status-debug-block-header">
        <span>{title}</span>
        <button
          type="button"
          className="assistant-status-debug-copy"
          aria-label={copied ? `Copied ${title}` : `Copy ${title}`}
          onClick={() => {
            copyToClipboard(text);
            setCopied(true);
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>{text}</pre>
    </section>
  );
}
