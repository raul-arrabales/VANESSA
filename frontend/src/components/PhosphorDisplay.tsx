import type { CSSProperties } from "react";

export type DisplayFrame = readonly string[];

export type PhosphorDisplayProps = {
  label: string;
  frame: DisplayFrame;
  className?: string;
  litGlyph?: string;
  unlitGlyph?: string;
  hoverMode?: "none" | "soft-glow";
};

const BANNER_GLYPH_WIDTH = 7;
const BANNER_FRAME_HEIGHT = 7;
const BANNER_GAP = " ";
const SPACE_GLYPH = " ".repeat(BANNER_GLYPH_WIDTH);

const BANNER_FONT: Record<string, DisplayFrame> = {
  A: [
    "   #   ",
    "  # #  ",
    " #   # ",
    "#     #",
    "#######",
    "#     #",
    "#     #",
  ],
  B: [
    "###### ",
    "#     #",
    "#     #",
    "###### ",
    "#     #",
    "#     #",
    "###### ",
  ],
  C: [
    " ##### ",
    "#     #",
    "#      ",
    "#      ",
    "#      ",
    "#     #",
    " ##### ",
  ],
  D: [
    "###### ",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "###### ",
  ],
  E: [
    "#######",
    "#      ",
    "#      ",
    "#####  ",
    "#      ",
    "#      ",
    "#######",
  ],
  F: [
    "#######",
    "#      ",
    "#      ",
    "#####  ",
    "#      ",
    "#      ",
    "#      ",
  ],
  G: [
    " ##### ",
    "#     #",
    "#      ",
    "#  ####",
    "#     #",
    "#     #",
    " ##### ",
  ],
  H: [
    "#     #",
    "#     #",
    "#     #",
    "#######",
    "#     #",
    "#     #",
    "#     #",
  ],
  I: [
    "  ###  ",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
    "  ###  ",
  ],
  J: [
    "      #",
    "      #",
    "      #",
    "      #",
    "#     #",
    "#     #",
    " ##### ",
  ],
  K: [
    "#    # ",
    "#   #  ",
    "#  #   ",
    "###    ",
    "#  #   ",
    "#   #  ",
    "#    # ",
  ],
  L: [
    "#      ",
    "#      ",
    "#      ",
    "#      ",
    "#      ",
    "#      ",
    "#######",
  ],
  M: [
    "#     #",
    "##   ##",
    "# # # #",
    "#  #  #",
    "#     #",
    "#     #",
    "#     #",
  ],
  N: [
    "#     #",
    "##    #",
    "# #   #",
    "#  #  #",
    "#   # #",
    "#    ##",
    "#     #",
  ],
  O: [
    "#######",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "#######",
  ],
  P: [
    "###### ",
    "#     #",
    "#     #",
    "###### ",
    "#      ",
    "#      ",
    "#      ",
  ],
  Q: [
    " ##### ",
    "#     #",
    "#     #",
    "#     #",
    "#   # #",
    "#    # ",
    " #### #",
  ],
  R: [
    "###### ",
    "#     #",
    "#     #",
    "###### ",
    "#   #  ",
    "#    # ",
    "#     #",
  ],
  S: [
    " ##### ",
    "#     #",
    "#      ",
    " ##### ",
    "      #",
    "#     #",
    " ##### ",
  ],
  T: [
    "#######",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
  ],
  U: [
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    " ##### ",
  ],
  V: [
    "#     #",
    "#     #",
    "#     #",
    "#     #",
    " #   # ",
    "  # #  ",
    "   #   ",
  ],
  W: [
    "#     #",
    "#  #  #",
    "#  #  #",
    "#  #  #",
    "#  #  #",
    "#  #  #",
    " ## ## ",
  ],
  X: [
    "#     #",
    " #   # ",
    "  # #  ",
    "   #   ",
    "  # #  ",
    " #   # ",
    "#     #",
  ],
  Y: [
    "#     #",
    " #   # ",
    "  # #  ",
    "   #   ",
    "   #   ",
    "   #   ",
    "   #   ",
  ],
  Z: [
    "#######",
    "     # ",
    "    #  ",
    "   #   ",
    "  #    ",
    " #     ",
    "#######",
  ],
  " ": [
    SPACE_GLYPH,
    SPACE_GLYPH,
    SPACE_GLYPH,
    SPACE_GLYPH,
    SPACE_GLYPH,
    SPACE_GLYPH,
    SPACE_GLYPH,
  ],
};

function validateFrame(frame: DisplayFrame): DisplayFrame {
  if (frame.length === 0) {
    throw new Error("PhosphorDisplay frames must contain at least one row.");
  }

  const width = frame[0]?.length ?? 0;
  if (width === 0) {
    throw new Error("PhosphorDisplay frames must contain at least one column.");
  }

  for (const row of frame) {
    if (row.length !== width) {
      throw new Error("PhosphorDisplay frames must use a consistent row width.");
    }
  }

  return frame;
}

export function buildBannerFrame(text: string): DisplayFrame {
  const normalizedText = text.toUpperCase();
  const glyphs = Array.from(normalizedText, (character) => {
    const glyph = BANNER_FONT[character];
    if (!glyph) {
      throw new Error(`Unsupported banner character: ${character}`);
    }
    return glyph;
  });

  if (glyphs.length === 0) {
    return validateFrame(BANNER_FONT[" "]);
  }

  const rows = Array.from({ length: BANNER_FRAME_HEIGHT }, (_, rowIndex) => (
    glyphs
      .map((glyph) => glyph[rowIndex] ?? SPACE_GLYPH)
      .join(BANNER_GAP)
  ));

  return validateFrame(rows);
}

export default function PhosphorDisplay({
  label,
  frame,
  className,
  litGlyph = "#",
  unlitGlyph = "#",
  hoverMode = "none",
}: PhosphorDisplayProps): JSX.Element {
  const validatedFrame = validateFrame(frame);
  const columnCount = validatedFrame[0].length;
  const displayStyle = {
    "--display-columns": String(columnCount),
    "--display-rows": String(validatedFrame.length),
  } as CSSProperties;

  return (
    <span
      className={[
        "phosphor-display",
        hoverMode === "soft-glow" ? "phosphor-display--soft-glow" : null,
        className ?? null,
      ].filter(Boolean).join(" ")}
      data-testid="phosphor-display"
      style={displayStyle}
    >
      <span className="sr-only">{label}</span>
      <span className="phosphor-display__screen" aria-hidden="true">
        {validatedFrame.map((row, rowIndex) => (
          <span className="phosphor-display__row" key={`row-${rowIndex}`}>
            {Array.from(row).map((cell, columnIndex) => {
              const isLit = cell === "#";
              return (
                <span
                  key={`cell-${rowIndex}-${columnIndex}`}
                  className={[
                    "phosphor-display__cell",
                    isLit ? "phosphor-display__cell--lit" : "phosphor-display__cell--dim",
                  ].join(" ")}
                >
                  {isLit ? litGlyph : unlitGlyph}
                </span>
              );
            })}
          </span>
        ))}
      </span>
    </span>
  );
}
