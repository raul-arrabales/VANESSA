import type { CSSProperties } from "react";
import { MONOGRAM_FRAME, VANESSA_WORDMARK } from "./brandFrames";
import PhosphorDisplay, { buildBannerFrame } from "./PhosphorDisplay";

type VanessaBrandProps = {
  className?: string;
  hoverMode?: "none" | "soft-glow";
  variant?: "wordmark" | "monogram";
  label?: string;
};

type VanessaMonogramProps = Pick<VanessaBrandProps, "className" | "hoverMode" | "label">;
type VanessaWordmarkProps = Pick<VanessaBrandProps, "className" | "hoverMode" | "label">;

function VanessaMonogram({
  className,
  hoverMode = "none",
  label = VANESSA_WORDMARK,
}: VanessaMonogramProps): JSX.Element {
  return (
    <span
      className={[
        "vanessa-monogram",
        hoverMode === "soft-glow" ? "vanessa-monogram--soft-glow" : null,
        className ?? null,
      ].filter(Boolean).join(" ")}
      data-testid="vanessa-monogram"
    >
      <span className="sr-only">{label}</span>
      <span className="vanessa-monogram__screen" aria-hidden="true">
        {MONOGRAM_FRAME.map((row, rowIndex) => (
          <span
            className="vanessa-monogram__row"
            key={`row-${rowIndex}`}
            style={{ "--monogram-columns": String(row.length) } as CSSProperties}
          >
            {Array.from(row).map((cell, columnIndex) => (
              <span
                key={`cell-${rowIndex}-${columnIndex}`}
                className={[
                  "vanessa-monogram__cell",
                  cell === "#" ? "vanessa-monogram__cell--lit" : "vanessa-monogram__cell--dim",
                ].join(" ")}
              />
            ))}
          </span>
        ))}
      </span>
    </span>
  );
}

function VanessaWordmark({
  className,
  hoverMode = "none",
  label = VANESSA_WORDMARK,
}: VanessaWordmarkProps): JSX.Element {
  return (
    <PhosphorDisplay
      className={className}
      label={label}
      frame={buildBannerFrame(VANESSA_WORDMARK)}
      litGlyph="#"
      unlitGlyph="#"
      hoverMode={hoverMode}
    />
  );
}

export default function VanessaBrand({
  className,
  hoverMode = "none",
  variant = "wordmark",
  label = VANESSA_WORDMARK,
}: VanessaBrandProps): JSX.Element {
  if (variant === "monogram") {
    return <VanessaMonogram className={className} hoverMode={hoverMode} label={label} />;
  }

  return <VanessaWordmark className={className} hoverMode={hoverMode} label={label} />;
}
