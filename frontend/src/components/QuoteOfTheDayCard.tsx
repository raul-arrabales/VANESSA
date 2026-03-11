import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchQuoteOfTheDay, type QuoteOfTheDay } from "../api/quotes";

type QuoteLoadState = "loading" | "ready" | "error";

export default function QuoteOfTheDayCard(): JSX.Element {
  const { t, i18n } = useTranslation("common");
  const activeLanguage = i18n.resolvedLanguage?.split("-")[0] ?? "en";
  const [quote, setQuote] = useState<QuoteOfTheDay | null>(null);
  const [state, setState] = useState<QuoteLoadState>("loading");

  useEffect(() => {
    let cancelled = false;

    async function loadQuote(): Promise<void> {
      setState("loading");
      try {
        const nextQuote = await fetchQuoteOfTheDay(activeLanguage);
        if (cancelled) {
          return;
        }
        setQuote(nextQuote);
        setState("ready");
      } catch {
        if (cancelled) {
          return;
        }
        setState("error");
      }
    }

    void loadQuote();

    return () => {
      cancelled = true;
    };
  }, [activeLanguage]);

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
          </p>
        </div>
      )}
    </aside>
  );
}
