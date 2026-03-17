export type QuoteOfTheDay = {
  id: number;
  text: string;
  author: string;
  source_universe: string;
  tone: string;
  language: string;
  date: string;
  origin: string;
};

type QuoteOfTheDayResponse = {
  quote: QuoteOfTheDay;
};

type QuoteSelectionMode = "daily" | "random";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function fetchQuoteOfTheDay(
  language: string,
  selection: QuoteSelectionMode = "daily",
): Promise<QuoteOfTheDay> {
  const params = new URLSearchParams({ lang: language, selection });
  const response = await fetch(buildUrl(`/v1/content/quote-of-the-day?${params.toString()}`), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Unable to load quote of the day: HTTP ${response.status}`);
  }

  const payload = await response.json() as QuoteOfTheDayResponse;
  return payload.quote;
}
