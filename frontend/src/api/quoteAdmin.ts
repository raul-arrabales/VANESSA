import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

async function requestJson<T>(path: string, token: string, options: {
  method?: "GET" | "POST" | "PUT";
  body?: unknown;
} = {}): Promise<T> {
  const headers: HeadersInit = {
    Accept: "application/json",
    Authorization: `Bearer ${token}`,
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildUrl(path), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const maybeJson = await response.text();
  const payload = maybeJson ? JSON.parse(maybeJson) as Record<string, unknown> : {};
  if (!response.ok) {
    throw new ApiError(String(payload.message ?? payload.error ?? `HTTP ${response.status}`), response.status);
  }
  return payload as T;
}

export type QuoteAdminItem = {
  id: number;
  language: string;
  text: string;
  author: string;
  source_universe: string;
  tone: string;
  tags: string[];
  is_active: boolean;
  is_approved: boolean;
  origin: string;
  external_ref: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type QuoteSummary = {
  total: number;
  active: number;
  approved: number;
  by_language: Array<{ value: string; count: number }>;
  by_tone: Array<{ value: string; count: number }>;
  by_origin: Array<{ value: string; count: number }>;
};

export type QuoteListFilters = {
  language?: string;
  source_universe?: string;
  tone?: string;
  origin?: string;
  is_active?: string;
  is_approved?: string;
  created_from?: string;
  created_to?: string;
  query?: string;
};

export type QuoteListResult = {
  items: QuoteAdminItem[];
  page: number;
  page_size: number;
  total: number;
  filters: Record<string, string | boolean>;
};

export type QuotePayload = {
  language: string;
  text: string;
  author: string;
  source_universe: string;
  tone: string;
  tags: string[];
  is_active: boolean;
  is_approved: boolean;
  origin: string;
  external_ref: string;
};

export async function fetchQuoteSummary(token: string): Promise<QuoteSummary> {
  const response = await requestJson<{ summary: QuoteSummary }>("/v1/quotes/summary", token);
  return response.summary;
}

export async function fetchQuotes(
  token: string,
  page: number,
  pageSize: number,
  filters: QuoteListFilters,
): Promise<QuoteListResult> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });

  return requestJson<QuoteListResult>(`/v1/quotes?${params.toString()}`, token);
}

export async function fetchQuoteById(quoteId: number, token: string): Promise<QuoteAdminItem> {
  const response = await requestJson<{ quote: QuoteAdminItem }>(`/v1/quotes/${quoteId}`, token);
  return response.quote;
}

export async function createQuote(payload: QuotePayload, token: string): Promise<QuoteAdminItem> {
  const response = await requestJson<{ quote: QuoteAdminItem }>("/v1/quotes", token, {
    method: "POST",
    body: payload,
  });
  return response.quote;
}

export async function updateQuote(quoteId: number, payload: QuotePayload, token: string): Promise<QuoteAdminItem> {
  const response = await requestJson<{ quote: QuoteAdminItem }>(`/v1/quotes/${quoteId}`, token, {
    method: "PUT",
    body: payload,
  });
  return response.quote;
}
