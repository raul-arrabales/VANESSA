import { ApiError, buildUrl } from "../auth/authApi";

export type CloudTrafficDirection = "egress" | "ingress";

export type CloudTrafficEvent = {
  id: string;
  timestamp: string;
  direction: CloudTrafficDirection;
  phase: string;
  runtime_profile: string;
  source_service: string;
  capability?: string;
  operation?: string;
  provider_origin?: string;
  provider_key?: string;
  provider_slug?: string;
  endpoint_host?: string;
  status_code?: number;
  duration_ms?: number;
  request_id?: string;
};

export type StreamCloudTrafficEventsOptions = {
  signal?: AbortSignal;
  onEvent?: (event: CloudTrafficEvent) => void;
};

export async function streamCloudTrafficEvents(
  token: string,
  options: StreamCloudTrafficEventsOptions = {},
): Promise<void> {
  const response = await fetch(buildUrl("/v1/runtime/cloud-traffic/events"), {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      Authorization: `Bearer ${token}`,
    },
    signal: options.signal,
  });

  if (!response.ok) {
    const raw = await response.text();
    const parsed = raw ? JSON.parse(raw) as Record<string, unknown> : {};
    throw new ApiError(
      String(parsed.message ?? parsed.error ?? `HTTP ${response.status}`),
      response.status,
      parsed.error ? String(parsed.error) : undefined,
    );
  }

  if (!response.body) {
    throw new ApiError("Cloud traffic stream response body missing", 502, "stream_unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex >= 0) {
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      const parsedEvent = parseSseEvent(rawEvent);
      if (parsedEvent?.event === "cloud_traffic") {
        options.onEvent?.(parsedEvent.data as CloudTrafficEvent);
      }
      boundaryIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }
}

function parseSseEvent(rawEvent: string): { event: string; data: Record<string, unknown> } | null {
  const normalized = rawEvent.replace(/\r/g, "");
  const lines = normalized.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return { event: eventName, data: JSON.parse(dataLines.join("\n")) as Record<string, unknown> };
}
