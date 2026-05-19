import type { LifecycleStateDefinition } from "./types";

function truncateLifecycleLabelLine(line: string, maxLineLength: number): string {
  if (line.length <= maxLineLength) {
    return line;
  }
  if (maxLineLength <= 3) {
    return line.slice(0, maxLineLength);
  }
  return `${line.slice(0, maxLineLength - 3)}...`;
}

export function getLifecycleNodeLabelLines(label: string, maxLineLength = 16, maxLines = 2): string[] {
  const normalizedLabel = label.trim().replace(/\s+/g, " ");
  if (!normalizedLabel) {
    return [""];
  }

  const words = normalizedLabel.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    const nextLine = currentLine ? `${currentLine} ${word}` : word;
    if (nextLine.length <= maxLineLength) {
      currentLine = nextLine;
      continue;
    }
    if (currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      lines.push(truncateLifecycleLabelLine(word, maxLineLength));
      currentLine = "";
    }
  }

  if (currentLine) {
    lines.push(currentLine);
  }

  if (lines.length <= maxLines) {
    return lines.map((line) => truncateLifecycleLabelLine(line, maxLineLength));
  }

  const visibleLines = lines.slice(0, maxLines);
  visibleLines[maxLines - 1] = truncateLifecycleLabelLine(lines.slice(maxLines - 1).join(" "), maxLineLength);
  return visibleLines;
}

export function getLifecycleStatePosition(
  state: LifecycleStateDefinition,
  index: number,
  total: number,
): { x: number; y: number } {
  if (typeof state.x === "number" && typeof state.y === "number") {
    return { x: state.x, y: state.y };
  }
  const columns = Math.min(Math.max(total, 1), 4);
  const column = index % columns;
  const row = Math.floor(index / columns);
  return {
    x: 90 + column * 180,
    y: 78 + row * 120,
  };
}
