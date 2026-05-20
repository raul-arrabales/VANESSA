import type { LifecycleStateDefinition } from "./types";

const LIFECYCLE_NODE_WIDTH = 140;
const LIFECYCLE_NODE_HEIGHT = 56;
const LIFECYCLE_NODE_HORIZONTAL_INSET = 14;
const LIFECYCLE_NODE_VERTICAL_INSET = 10;
const LIFECYCLE_ADJACENT_CENTER_DISTANCE = 225;

type LifecyclePoint = {
  x: number;
  y: number;
};

type LifecycleAnchor = LifecyclePoint & {
  normalX: number;
  normalY: number;
};

type LifecycleEdgePathOptions = {
  laneOffset?: number;
};

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

function clampCoordinate(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function formatLifecycleCoordinate(value: number): string {
  return Number(value.toFixed(2)).toString();
}

function getLifecycleNodeAnchor(from: LifecyclePoint, to: LifecyclePoint): LifecycleAnchor {
  const halfWidth = LIFECYCLE_NODE_WIDTH / 2;
  const halfHeight = LIFECYCLE_NODE_HEIGHT / 2;
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  if (dx === 0 && dy === 0) {
    return {
      x: from.x + halfWidth,
      y: from.y,
      normalX: 1,
      normalY: 0,
    };
  }

  if (Math.abs(dx) / halfWidth > Math.abs(dy) / halfHeight) {
    const direction = dx > 0 ? 1 : -1;
    const y = from.y + dy * (halfWidth / Math.abs(dx));
    return {
      x: from.x + direction * halfWidth,
      y: clampCoordinate(
        y,
        from.y - halfHeight + LIFECYCLE_NODE_VERTICAL_INSET,
        from.y + halfHeight - LIFECYCLE_NODE_VERTICAL_INSET,
      ),
      normalX: direction,
      normalY: 0,
    };
  }

  const direction = dy > 0 ? 1 : -1;
  const x = from.x + dx * (halfHeight / Math.abs(dy));
  return {
    x: clampCoordinate(
      x,
      from.x - halfWidth + LIFECYCLE_NODE_HORIZONTAL_INSET,
      from.x + halfWidth - LIFECYCLE_NODE_HORIZONTAL_INSET,
    ),
    y: from.y + direction * halfHeight,
    normalX: 0,
    normalY: direction,
  };
}

function getLifecycleCurveBend(start: LifecyclePoint, end: LifecyclePoint): number {
  const distance = Math.hypot(end.x - start.x, end.y - start.y);
  return clampCoordinate(distance * 0.12, 12, 34);
}

function getLifecycleControlDistance(start: LifecyclePoint, end: LifecyclePoint): number {
  const distance = Math.hypot(end.x - start.x, end.y - start.y);
  return clampCoordinate(distance * 0.34, 8, 108);
}

function isAdjacentLifecycleEdge(start: LifecyclePoint, end: LifecyclePoint): boolean {
  return Math.hypot(end.x - start.x, end.y - start.y) <= LIFECYCLE_ADJACENT_CENTER_DISTANCE;
}

export function buildLifecycleEdgePath(start: LifecyclePoint, end: LifecyclePoint, options: LifecycleEdgePathOptions = {}): string {
  const startAnchor = getLifecycleNodeAnchor(start, end);
  const endAnchor = getLifecycleNodeAnchor(end, start);
  const distance = Math.hypot(endAnchor.x - startAnchor.x, endAnchor.y - startAnchor.y);

  if (distance === 0) {
    const loopControlX = startAnchor.x + 58;
    return [
      `M ${formatLifecycleCoordinate(startAnchor.x)} ${formatLifecycleCoordinate(startAnchor.y)}`,
      `C ${formatLifecycleCoordinate(loopControlX)} ${formatLifecycleCoordinate(startAnchor.y - 42)},`,
      `${formatLifecycleCoordinate(loopControlX)} ${formatLifecycleCoordinate(startAnchor.y + 42)},`,
      `${formatLifecycleCoordinate(startAnchor.x)} ${formatLifecycleCoordinate(startAnchor.y)}`,
    ].join(" ");
  }

  const perpendicularX = -(endAnchor.y - startAnchor.y) / distance;
  const perpendicularY = (endAnchor.x - startAnchor.x) / distance;
  const laneOffset = options.laneOffset ?? 0;
  const shiftedStart = {
    x: startAnchor.x + perpendicularX * laneOffset,
    y: startAnchor.y + perpendicularY * laneOffset,
  };
  const shiftedEnd = {
    x: endAnchor.x + perpendicularX * laneOffset,
    y: endAnchor.y + perpendicularY * laneOffset,
  };

  if (isAdjacentLifecycleEdge(start, end)) {
    return [
      `M ${formatLifecycleCoordinate(shiftedStart.x)} ${formatLifecycleCoordinate(shiftedStart.y)}`,
      `L ${formatLifecycleCoordinate(shiftedEnd.x)} ${formatLifecycleCoordinate(shiftedEnd.y)}`,
    ].join(" ");
  }

  const bend = getLifecycleCurveBend(startAnchor, endAnchor);
  const controlDistance = getLifecycleControlDistance(startAnchor, endAnchor);
  const startControl = {
    x: startAnchor.x + startAnchor.normalX * controlDistance + perpendicularX * (bend + laneOffset),
    y: startAnchor.y + startAnchor.normalY * controlDistance + perpendicularY * (bend + laneOffset),
  };
  const endControl = {
    x: endAnchor.x + endAnchor.normalX * controlDistance + perpendicularX * (bend + laneOffset),
    y: endAnchor.y + endAnchor.normalY * controlDistance + perpendicularY * (bend + laneOffset),
  };

  return [
    `M ${formatLifecycleCoordinate(shiftedStart.x)} ${formatLifecycleCoordinate(shiftedStart.y)}`,
    `C ${formatLifecycleCoordinate(startControl.x)} ${formatLifecycleCoordinate(startControl.y)},`,
    `${formatLifecycleCoordinate(endControl.x)} ${formatLifecycleCoordinate(endControl.y)},`,
    `${formatLifecycleCoordinate(shiftedEnd.x)} ${formatLifecycleCoordinate(shiftedEnd.y)}`,
  ].join(" ");
}
