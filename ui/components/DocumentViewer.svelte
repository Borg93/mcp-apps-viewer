<script lang="ts">
import { onMount, onDestroy } from "svelte";
import type { App } from "@modelcontextprotocol/ext-apps";
import type { TextLine, ViewerData, PageData, PageAltoData, TooltipState } from "../lib/types";
import { parsePageResult } from "../lib/utils";

interface Props {
  app: App;
  data: ViewerData;
  displayMode?: "inline" | "fullscreen";
}

let { app, data, displayMode = "inline" }: Props = $props();

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let overlaysVisible = $state(true);
let currentPageIndex = $state(0);
let tooltip = $state<TooltipState | null>(null);
let highlightedLineId = $state<string | null>(null);
let status = $state("");
let loading = $state(false);
let isFullscreen = $state(false);

let totalPages = $derived(data.pageUrls.length);
let effectiveFullscreen = $derived(isFullscreen || displayMode === "fullscreen");

// Client-side page cache — each page fetched at most once
let pageCache = new Map<number, PageData>();

// Canvas + transform
let canvasEl: HTMLCanvasElement;
let containerEl: HTMLDivElement;
let wrapperEl: HTMLDivElement;
let image: HTMLImageElement | null = null;
let transform = { x: 0, y: 0, scale: 1 };

// Current page ALTO data
let currentAlto: PageAltoData | null = null;

// Parsed polygon data for hit testing (image coordinates)
let currentPolygons: { lineId: string; points: number[]; line: TextLine }[] = [];

// Pointer state for pan + click detection
let pointerDown: { x: number; y: number; tx: number; ty: number } | null = null;
let dragged = false;

// Animation frame handle
let rafId = 0;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Parse ALTO polygon "x1,y1 x2,y2 ..." into flat [x1,y1,x2,y2,...] */
function parsePolygonPoints(polygon: string): number[] {
  const pts: number[] = [];
  for (const pair of polygon.trim().split(/\s+/)) {
    const [x, y] = pair.split(",").map(Number);
    if (!isNaN(x) && !isNaN(y)) pts.push(x, y);
  }
  return pts;
}

/** Ray-casting point-in-polygon test */
function pointInPolygon(px: number, py: number, pts: number[]): boolean {
  let inside = false;
  for (let i = 0, j = pts.length - 2; i < pts.length; j = i, i += 2) {
    const xi = pts[i], yi = pts[i + 1];
    const xj = pts[j], yj = pts[j + 1];
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function findLineAtImageCoord(imgX: number, imgY: number) {
  for (const p of currentPolygons) {
    if (pointInPolygon(imgX, imgY, p.points)) return p;
  }
  return null;
}

/** Convert screen (canvas-relative) coords to image pixel coords */
function screenToImage(sx: number, sy: number): { x: number; y: number } {
  return {
    x: (sx - transform.x) / transform.scale,
    y: (sy - transform.y) / transform.scale,
  };
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

function draw() {
  if (!canvasEl || !image) return;
  const ctx = canvasEl.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvasEl.clientWidth;
  const h = canvasEl.clientHeight;

  if (canvasEl.width !== w * dpr || canvasEl.height !== h * dpr) {
    canvasEl.width = w * dpr;
    canvasEl.height = h * dpr;
  }

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.scale, transform.scale);

  ctx.drawImage(image, 0, 0);

  if (overlaysVisible && currentPolygons.length > 0) {
    for (const p of currentPolygons) {
      const isHighlighted = p.lineId === highlightedLineId;
      ctx.beginPath();
      ctx.moveTo(p.points[0], p.points[1]);
      for (let i = 2; i < p.points.length; i += 2) {
        ctx.lineTo(p.points[i], p.points[i + 1]);
      }
      ctx.closePath();

      ctx.fillStyle = isHighlighted ? "rgba(193, 95, 60, 0.3)" : "rgba(193, 95, 60, 0.15)";
      ctx.fill();
      ctx.strokeStyle = isHighlighted ? "rgba(193, 95, 60, 1)" : "rgba(193, 95, 60, 0.7)";
      ctx.lineWidth = isHighlighted ? 3 / transform.scale : 2 / transform.scale;
      ctx.stroke();
    }
  }

  ctx.restore();
}

function requestDraw() {
  if (!rafId) {
    rafId = requestAnimationFrame(() => {
      rafId = 0;
      draw();
    });
  }
}

function fitToCanvas() {
  if (!image || !canvasEl) return;
  const cw = canvasEl.clientWidth;
  const ch = canvasEl.clientHeight;
  const padding = 16;
  const scaleX = (cw - padding * 2) / image.naturalWidth;
  const scaleY = (ch - padding * 2) / image.naturalHeight;
  transform.scale = Math.min(scaleX, scaleY, 1);
  transform.x = (cw - image.naturalWidth * transform.scale) / 2;
  transform.y = (ch - image.naturalHeight * transform.scale) / 2;
}

// ---------------------------------------------------------------------------
// Pointer interaction (pan + click + hover)
// ---------------------------------------------------------------------------

function handlePointerDown(e: PointerEvent) {
  if (e.button !== 0) return;
  pointerDown = { x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y };
  dragged = false;
  canvasEl.setPointerCapture(e.pointerId);
}

function handlePointerMove(e: PointerEvent) {
  const rect = canvasEl.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;

  if (pointerDown) {
    const dx = e.clientX - pointerDown.x;
    const dy = e.clientY - pointerDown.y;
    if (dx * dx + dy * dy > 9) dragged = true;
    transform.x = pointerDown.tx + dx;
    transform.y = pointerDown.ty + dy;
    requestDraw();
    return;
  }

  if (!overlaysVisible || !currentPolygons.length) {
    if (tooltip) { tooltip = null; highlightedLineId = null; requestDraw(); }
    return;
  }

  const img = screenToImage(cx, cy);
  const hit = findLineAtImageCoord(img.x, img.y);
  if (hit) {
    tooltip = { text: hit.line.transcription, x: e.clientX + 15, y: e.clientY + 15 };
    if (highlightedLineId !== hit.lineId) {
      highlightedLineId = hit.lineId;
      requestDraw();
    }
    canvasEl.style.cursor = "pointer";
  } else {
    if (tooltip) {
      tooltip = null;
      highlightedLineId = null;
      requestDraw();
    }
    canvasEl.style.cursor = pointerDown ? "grabbing" : "grab";
  }
}

function handlePointerUp(e: PointerEvent) {
  if (!pointerDown) return;
  const wasDrag = dragged;
  pointerDown = null;
  canvasEl.releasePointerCapture(e.pointerId);

  if (wasDrag) return;

  if (!overlaysVisible || !currentPolygons.length) return;
  const rect = canvasEl.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;
  const img = screenToImage(cx, cy);
  const hit = findLineAtImageCoord(img.x, img.y);
  if (hit) sendLineText(hit.line);
}

function handlePointerLeave() {
  tooltip = null;
  if (highlightedLineId) {
    highlightedLineId = null;
    requestDraw();
  }
}

function handleWheel(e: WheelEvent) {
  e.preventDefault();
  const rect = canvasEl.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;

  const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
  const newScale = Math.max(0.1, Math.min(10, transform.scale * factor));

  transform.x = cx - (cx - transform.x) * (newScale / transform.scale);
  transform.y = cy - (cy - transform.y) * (newScale / transform.scale);
  transform.scale = newScale;
  requestDraw();
}

// ---------------------------------------------------------------------------
// Page rendering + navigation
// ---------------------------------------------------------------------------

/** Render a PageData that's already available */
function renderPage(page: PageData) {
  currentAlto = page.alto;
  currentPolygons = [];
  highlightedLineId = null;
  tooltip = null;

  if (currentAlto?.textLines) {
    for (const line of currentAlto.textLines) {
      const points = parsePolygonPoints(line.polygon);
      if (points.length >= 6) {
        currentPolygons.push({ lineId: line.id, points, line });
      }
    }
  }

  const img = new Image();
  img.onload = () => {
    image = img;
    fitToCanvas();
    draw();
    status = currentPolygons.length > 0
      ? `${currentPolygons.length} text lines`
      : "No text overlay";
    setTimeout(() => (status = ""), 3000);
    updatePageContext();
  };
  img.onerror = () => {
    status = "Failed to load image";
    image = null;
    draw();
  };
  img.src = page.imageDataUrl;
}

/** Navigate to a page — use cache or fetch via callServerTool */
async function goToPage(index: number) {
  if (index < 0 || index >= totalPages || loading) return;
  currentPageIndex = index;

  // Check cache first — instant render, no server call
  const cached = pageCache.get(index);
  if (cached) {
    renderPage(cached);
    return;
  }

  // Fetch from server via callServerTool (same pattern as wiki-explorer)
  loading = true;
  status = `Loading page ${index + 1}...`;

  try {
    const urls = data.pageUrls[index];
    const result = await app.callServerTool({
      name: "load-page",
      arguments: {
        image_url: urls.image,
        alto_url: urls.alto,
        page_index: index,
      },
    });

    if (result.isError) {
      const errText = result.content?.map((c: any) => ("text" in c ? c.text : "")).join(" ") ?? "Unknown error";
      console.error("load-page error:", errText);
      status = `Error loading page ${index + 1}`;
      return;
    }

    const page = parsePageResult(result);
    if (page) {
      pageCache.set(index, page);
      // Only render if user hasn't navigated away during fetch
      if (currentPageIndex === index) {
        renderPage(page);
      }
    } else {
      status = "Failed to parse page data";
    }
  } catch (e) {
    console.error("load-page failed:", e);
    status = `Failed to load page ${index + 1}`;
  } finally {
    loading = false;
  }
}

function toggleOverlays() {
  overlaysVisible = !overlaysVisible;
  requestDraw();
}

function toggleFullscreen() {
  isFullscreen = !isFullscreen;
  requestAnimationFrame(() => {
    fitToCanvas();
    draw();
  });
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && isFullscreen) {
    isFullscreen = false;
    requestAnimationFrame(() => {
      fitToCanvas();
      draw();
    });
  }
}

// ---------------------------------------------------------------------------
// Model context + text selection
// ---------------------------------------------------------------------------

async function updatePageContext() {
  if (!app) return;
  const page = currentPageIndex + 1;
  const lineCount = currentAlto?.textLines?.length ?? 0;
  const sampleLines = currentAlto?.textLines
    ?.slice(0, 5)
    .map(l => l.transcription)
    .join("\n") ?? "";

  try {
    await app.updateModelContext({
      content: [{
        type: "text",
        text: [
          `Document viewer: page ${page}/${totalPages}`,
          lineCount > 0 ? `${lineCount} transcribed text lines.` : "No transcribed text.",
          sampleLines ? `First lines:\n${sampleLines}` : "",
        ].filter(Boolean).join("\n"),
      }],
    });
  } catch (e) {
    console.error("[updateModelContext]", e);
  }
}

async function sendLineText(line: TextLine) {
  status = "Sending selected text...";
  try {
    await app.sendMessage({
      role: "user",
      content: [{ type: "text", text: `Selected text from page ${currentPageIndex + 1}/${totalPages}:\n"${line.transcription}"` }],
    });
    status = "Text sent";
  } catch (e) {
    console.error(e);
    status = "Failed to send text";
  } finally {
    setTimeout(() => (status = ""), 2000);
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

let resizeObserver: ResizeObserver | null = null;

onMount(() => {
  resizeObserver = new ResizeObserver(() => {
    if (image) {
      fitToCanvas();
      draw();
    }
  });
  resizeObserver.observe(containerEl);

  // Seed cache with first page from initial data
  pageCache.set(0, data.firstPage);
  renderPage(data.firstPage);
});

onDestroy(() => {
  resizeObserver?.disconnect();
  if (rafId) cancelAnimationFrame(rafId);
});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="viewer-wrapper"
  class:fullscreen={effectiveFullscreen}
  bind:this={wrapperEl}
>
  <!-- Controls -->
  <div class="controls">
    <button class="control-btn" class:active={overlaysVisible} onclick={toggleOverlays}>
      {overlaysVisible ? "Hide Overlays" : "Show Overlays"}
    </button>

    {#if totalPages > 1}
      <div class="page-nav">
        <button class="control-btn" onclick={() => goToPage(currentPageIndex - 1)} disabled={currentPageIndex === 0 || loading}>
          Prev
        </button>
        <span class="page-indicator">
          {#if loading}
            Loading...
          {:else}
            Page {currentPageIndex + 1} / {totalPages}
          {/if}
        </span>
        <button class="control-btn" onclick={() => goToPage(currentPageIndex + 1)} disabled={currentPageIndex === totalPages - 1 || loading}>
          Next
        </button>
      </div>
    {/if}

    <button class="control-btn fullscreen-btn" onclick={toggleFullscreen}>
      {effectiveFullscreen ? "Exit Fullscreen" : "Fullscreen"}
    </button>

    {#if status}
      <span class="page-status">{status}</span>
    {/if}
  </div>

  <!-- Canvas -->
  <div class="canvas-container" bind:this={containerEl}>
    <canvas
      bind:this={canvasEl}
      style="cursor: grab"
      onpointerdown={handlePointerDown}
      onpointermove={handlePointerMove}
      onpointerup={handlePointerUp}
      onpointerleave={handlePointerLeave}
      onwheel={handleWheel}
    ></canvas>
  </div>
</div>

<!-- Tooltip -->
{#if tooltip && tooltip.x > 0}
  <div class="tooltip" style:left="{tooltip.x}px" style:top="{tooltip.y}px">
    {tooltip.text}
  </div>
{/if}

<style>
.viewer-wrapper {
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 0.75rem);
  min-height: 60vh;
}
.viewer-wrapper.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 999;
  min-height: 0;
  height: 100vh;
  background: var(--color-background-primary, #fff);
  padding: var(--spacing-sm, 0.5rem);
}

.controls {
  display: flex;
  gap: var(--spacing-sm, 0.5rem);
  align-items: center;
  flex-wrap: wrap;
}
.page-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 0.25rem);
}
.page-indicator {
  font-size: var(--font-text-sm-size, 0.875rem);
  color: var(--color-text-secondary);
  white-space: nowrap;
  min-width: 80px;
  text-align: center;
}
.page-status {
  font-size: var(--font-text-sm-size, 0.875rem);
  color: var(--color-text-secondary);
}

.control-btn {
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
  min-width: 80px;
  background: var(--color-background-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--border-radius-md, 6px);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--font-text-sm-size, 0.875rem);
  transition: all 0.2s ease;
}
.control-btn:hover {
  background: var(--color-background-tertiary);
  border-color: var(--color-accent);
}
.control-btn.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-text-on-accent);
}
.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.fullscreen-btn {
  margin-left: auto;
}

.canvas-container {
  width: 100%;
  flex: 1;
  background: var(--color-background-secondary, #f5f5f5);
  border-radius: var(--border-radius-lg, 10px);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
  min-height: 400px;
  position: relative;
}
.viewer-wrapper.fullscreen .canvas-container {
  min-height: 0;
  border-radius: var(--border-radius-md, 6px);
}
.canvas-container canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.tooltip {
  position: fixed;
  background: var(--color-tooltip-background, #333);
  color: var(--color-tooltip-text, #fff);
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 0.75rem);
  border-radius: var(--border-radius-md, 6px);
  font-size: var(--font-text-sm-size, 0.875rem);
  pointer-events: none;
  z-index: 1000;
  max-width: 300px;
  word-wrap: break-word;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>
