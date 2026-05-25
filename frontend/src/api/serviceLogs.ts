import { ApiError, buildUrl, requestJson } from "../auth/authApi";

export type ServiceLogCatalogEntry = {
  id: string;
  display_name: string;
};

export type ServiceLogEntry = {
  id: string;
  service: string;
  timestamp: string | null;
  level: string;
  event_type: string;
  raw: string;
  message: string;
};

export type ServiceLogSnapshot = {
  service: string;
  display_name: string;
  tail: number;
  entries: ServiceLogEntry[];
};

export type StreamServiceLogsOptions = {
  signal?: AbortSignal;
  since?: string;
  level?: string;
  onEvent?: (event: ServiceLogEntry) => void;
  onError?: (error: ApiError) => void;
};

export async function fetchServiceLogServices(token: string): Promise<ServiceLogCatalogEntry[]> {
  const payload = await requestJson<{ services: ServiceLogCatalogEntry[] }>("/v1/system/logs/services", { token });
  return payload.services;
}

export async function fetchServiceLogSnapshot(
  token: string,
  service: string,
  options: { tail?: number; since?: string; level?: string } = {},
): Promise<ServiceLogSnapshot> {
  const params = new URLSearchParams();
  if (typeof options.tail === "number") {
    params.set("tail", String(options.tail));
  }
  if (options.since) {
    params.set("since", options.since);
  }
  if (options.level) {
    params.set("level", options.level);
  }
  const query = params.toString();
  return requestJson<ServiceLogSnapshot>(`/v1/system/logs/${encodeURIComponent(service)}${query ? `?${query}` : ""}`, { token });
}

export async function streamServiceLogs(
  token: string,
  service: string,
  options: StreamServiceLogsOptions = {},
): Promise<void> {
  const params = new URLSearchParams();
  if (options.since) {
    params.set("since", options.since);
  }
  if (options.level) {
    params.set("level", options.level);
  }
  const query = params.toString();
  const response = await fetch(buildUrl(`/v1/system/logs/${encodeURIComponent(service)}/events${query ? `?${query}` : ""}`), {
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
    throw new ApiError("Service log stream response body missing", 502, "stream_unavailable");
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
      if (parsedEvent?.event === "service_log") {
        options.onEvent?.(parsedEvent.data as ServiceLogEntry);
      }
      if (parsedEvent?.event === "service_log_error") {
        options.onError?.(
          new ApiError(
            String(parsedEvent.data.message ?? "Service log stream failed"),
            503,
            parsedEvent.data.error ? String(parsedEvent.data.error) : undefined,
          ),
        );
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
