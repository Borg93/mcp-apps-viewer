/**
 * Polygon overlay drawing and highlight resolution — pure functions, no Svelte dependencies.
 */

import type { PolygonHit } from "./geometry";
import type { TextLine, HighlightCommand } from "./types";
import type { Transform } from "./canvas";

export interface PolygonStyle {
  color: string;
  thickness: number;
  opacity: number;
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Draw polygon overlays on a canvas context (already transformed to image space).
 */
export function drawPolygonOverlays(
  ctx: CanvasRenderingContext2D,
  transform: Transform,
  polygons: PolygonHit[],
  style: PolygonStyle,
  hoveredLineId: string | null,
  externalIds: Set<string>,
  externalColor: string | null,
): void {
  if (polygons.length === 0) return;

  for (const p of polygons) {
    const isHovered = p.lineId === hoveredLineId;
    const isExternal = externalIds.has(p.lineId);

    ctx.beginPath();
    ctx.moveTo(p.points[0], p.points[1]);
    for (let i = 2; i < p.points.length; i += 2) {
      ctx.lineTo(p.points[i], p.points[i + 1]);
    }
    ctx.closePath();

    if (isExternal && externalColor) {
      ctx.fillStyle = hexToRgba(externalColor, 0.45);
      ctx.fill();
      ctx.strokeStyle = hexToRgba(externalColor, 1);
      ctx.lineWidth = 3 / transform.scale;
      ctx.stroke();
    } else {
      ctx.fillStyle = isHovered
        ? hexToRgba(style.color, Math.min(1, style.opacity * 2))
        : hexToRgba(style.color, style.opacity);
      ctx.fill();
      ctx.strokeStyle = isHovered
        ? hexToRgba(style.color, 1)
        : hexToRgba(style.color, Math.min(1, style.opacity * 5));
      ctx.lineWidth = isHovered
        ? (style.thickness + 1) / transform.scale
        : style.thickness / transform.scale;
      ctx.stroke();
    }
  }
}

/**
 * Resolve a HighlightCommand to concrete line IDs.
 * Uses lineIds directly if provided, otherwise falls back to text search.
 */
export function resolveHighlightIds(
  command: HighlightCommand,
  textLines: TextLine[],
): string[] {
  if (command.lineIds.length > 0) return command.lineIds;
  if (!command.searchText || textLines.length === 0) return [];
  const needle = command.searchText.toLowerCase();
  return textLines
    .filter(l => l.transcription.toLowerCase().includes(needle))
    .map(l => l.id);
}
