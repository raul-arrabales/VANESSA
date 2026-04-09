export function getCurrentTimeMs(): number {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    const currentTime = performance.now();
    if (Number.isFinite(currentTime)) {
      return currentTime;
    }
  }
  return Date.now();
}

export function formatElapsedDuration(durationMs: number, locale?: string): string {
  if (!Number.isFinite(durationMs) || durationMs < 0) {
    return "0 ms";
  }

  if (durationMs < 1000) {
    return `${Math.round(durationMs)} ms`;
  }

  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(durationMs / 1000)} s`;
}
