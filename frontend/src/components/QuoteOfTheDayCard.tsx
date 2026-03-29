import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchQuoteOfTheDay, type QuoteOfTheDay } from "../api/quotes";

type QuoteLoadState = "loading" | "ready" | "error";

export default function QuoteOfTheDayCard(): JSX.Element {
  const { t, i18n } = useTranslation("common");
  const activeLanguage = i18n.resolvedLanguage?.split("-")[0] ?? "en";
  const [quote, setQuote] = useState<QuoteOfTheDay | null>(null);
  const [state, setState] = useState<QuoteLoadState>("loading");
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function loadQuote(options?: { preserveCurrentQuote?: boolean }): Promise<void> {
    if (options?.preserveCurrentQuote) {
      setIsRefreshing(true);
    } else {
      setState("loading");
    }

    const nextQuote = await fetchQuoteOfTheDay(
      activeLanguage,
      options?.preserveCurrentQuote ? "random" : "daily",
    );
    setQuote(nextQuote);
    setState("ready");
    setIsRefreshing(false);
  }

  useEffect(() => {
    let cancelled = false;

    async function syncQuote(): Promise<void> {
      try {
        const nextQuote = await fetchQuoteOfTheDay(activeLanguage, "daily");
        if (cancelled) {
          return;
        }
        setQuote(nextQuote);
        setState("ready");
      } catch {
        if (cancelled) {
          return;
        }
        setIsRefreshing(false);
        setState("error");
      }
    }

    void syncQuote();

    return () => {
      cancelled = true;
    };
  }, [activeLanguage]);

  const refreshQuote = async (): Promise<void> => {
    try {
      await loadQuote({ preserveCurrentQuote: true });
    } catch {
      setIsRefreshing(false);
      setState("error");
    }
  };

  return (
    <aside className="quote-card" aria-live="polite">
      <div className="quote-card-header">
        <p className="field-label quote-card-eyebrow">{t("quoteOfTheDay.eyebrow")}</p>
        <h3 className="section-title quote-card-title">{t("quoteOfTheDay.title")}</h3>
      </div>
      {state === "loading" && (
        <p className="status-text">{t("quoteOfTheDay.loading")}</p>
      )}
      {state === "error" && (
        <p className="status-text">{t("quoteOfTheDay.error")}</p>
      )}
      {quote && state === "ready" && (
        <div className="card-stack">
          <blockquote className="quote-card-body">
            <p>{quote.text}</p>
          </blockquote>
          <p className="quote-card-meta">
            <span>{quote.author}</span>
            <span aria-hidden="true">/</span>
            <span>{quote.source_universe}</span>
            <span aria-hidden="true">/</span>
            <span>{t(`quoteOfTheDay.tones.${quote.tone}`, quote.tone)}</span>
            <button
              className="btn btn-ghost quote-card-refresh"
              type="button"
              onClick={() => void refreshQuote()}
              disabled={isRefreshing}
            >
              {isRefreshing ? t("quoteOfTheDay.refreshing") : t("quoteOfTheDay.refresh")}
            </button>
          </p>
        </div>
      )}
    </aside>
  );
}
