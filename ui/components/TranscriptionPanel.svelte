<script lang="ts">
import type { TextLine } from "../lib/types";

interface Props {
  textLines: TextLine[];
  highlightedLineId: string | null;
  onLineHover: (id: string | null) => void;
  onLineClick: (line: TextLine) => void;
  onClose: () => void;
}

let { textLines, highlightedLineId, onLineHover, onLineClick, onClose }: Props = $props();

let lineEls: HTMLDivElement[] = [];
let containerEl: HTMLDivElement;

// Auto-scroll to highlighted line when changed externally (from canvas hover)
$effect(() => {
  const id = highlightedLineId;
  if (!id || !containerEl) return;
  const idx = textLines.findIndex(l => l.id === id);
  if (idx >= 0 && lineEls[idx]) {
    const el = lineEls[idx];
    const containerRect = containerEl.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    if (elRect.top < containerRect.top || elRect.bottom > containerRect.bottom) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="panel">
  <div class="panel-header">
    <span class="panel-title">Transcription</span>
    <button class="panel-close" onclick={onClose} title="Close panel">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </button>
  </div>
  <div class="panel-lines" bind:this={containerEl}>
    {#each textLines as line, i}
      <button
        class="line-item"
        class:highlighted={line.id === highlightedLineId}
        bind:this={lineEls[i]}
        onpointerenter={() => onLineHover(line.id)}
        onpointerleave={() => onLineHover(null)}
        onclick={() => onLineClick(line)}
      >
        {line.transcription}
      </button>
    {/each}
    {#if textLines.length === 0}
      <div class="no-lines">No transcribed text on this page</div>
    {/if}
  </div>
</div>

<style>
.panel {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  display: flex;
  flex-direction: column;
  background: var(--color-background-primary, light-dark(#faf9f5, #1a1815));
  border-right: 1px solid var(--color-border-primary, light-dark(#d4d2cb, #3a3632));
  z-index: 10;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
  border-bottom: 1px solid var(--color-border-primary, light-dark(#d4d2cb, #3a3632));
  flex-shrink: 0;
}

.panel-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary, light-dark(#5c5c5c, #a8a6a3));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.panel-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: var(--border-radius-sm, 4px);
  background: transparent;
  color: var(--color-text-secondary, light-dark(#5c5c5c, #a8a6a3));
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}

.panel-close:hover {
  opacity: 1;
}

.panel-lines {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xs, 0.25rem) 0;
}

.line-item {
  display: block;
  width: 100%;
  padding: var(--spacing-xs, 0.25rem) var(--spacing-md, 1rem);
  font: inherit;
  font-size: var(--font-text-sm-size, 0.875rem);
  line-height: 1.5;
  text-align: left;
  color: var(--color-text-primary, light-dark(#2c2c2c, #e8e6e3));
  background: none;
  border: none;
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
}

.line-item:hover,
.line-item.highlighted {
  background: var(--claude-selection, rgba(193, 95, 60, 0.19));
  border-left-color: var(--color-accent, #c15f3c);
}

.no-lines {
  padding: var(--spacing-lg, 1.5rem) var(--spacing-md, 1rem);
  color: var(--color-text-secondary, light-dark(#5c5c5c, #a8a6a3));
  font-size: var(--font-text-sm-size, 0.875rem);
  font-style: italic;
  text-align: center;
}
</style>
