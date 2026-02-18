<script lang="ts">
import { onMount } from "svelte";
import {
  App,
  applyDocumentTheme,
  applyHostFonts,
  applyHostStyleVariables,
  type McpUiHostContext,
} from "@modelcontextprotocol/ext-apps";

import DocumentViewer from "./components/DocumentViewer.svelte";
import EmptyState from "./components/EmptyState.svelte";

import type { ViewerData } from "./lib/types";
import { parseToolResult } from "./lib/utils";

const DEFAULT_INLINE_HEIGHT = 300;

let app = $state<App | null>(null);
let hostContext = $state<McpUiHostContext | undefined>();
let viewerData = $state<ViewerData | null>(null);
let error = $state<string | null>(null);
let displayMode = $state<"inline" | "fullscreen">("inline");

let hasData = $derived(viewerData && viewerData.pageUrls.length > 0);
let isCardState = $derived(!hasData || !!error || !app);

$effect(() => {
  if (hostContext?.theme) applyDocumentTheme(hostContext.theme);
  if (hostContext?.styles?.variables) applyHostStyleVariables(hostContext.styles.variables);
  if (hostContext?.styles?.css?.fonts) applyHostFonts(hostContext.styles.css.fonts);
  if (hostContext?.displayMode) displayMode = hostContext.displayMode as "inline" | "fullscreen";
});

$effect(() => {
  if (!app || displayMode === "fullscreen") return;
  const height = isCardState ? DEFAULT_INLINE_HEIGHT : 600;
  setTimeout(() => app?.sendSizeChanged({ height }), 50);
});

onMount(async () => {
  const instance = new App(
    { name: "Document Viewer", version: "1.0.0" },
    {},
    { autoResize: false },
  );

  instance.ontoolinput = (params) => {
    console.info("Tool input:", params);
  };

  instance.ontoolresult = (result) => {
    console.info("Tool result:", result);
    if (result.isError) {
      error = result.content?.map((c: any) => ("text" in c ? c.text : "")).join(" ") ?? "Unknown error";
      return;
    }
    const data = parseToolResult(result);
    if (data) {
      viewerData = data;
      error = null;
    } else {
      error = "Failed to parse tool result";
    }
  };

  instance.ontoolcancelled = (params) => {
    error = `Cancelled: ${params.reason}`;
  };

  instance.onerror = (err) => {
    console.error("App error:", err);
    error = err.message;
  };

  instance.onhostcontextchanged = (params) => {
    hostContext = { ...hostContext, ...params };
  };

  await instance.connect();
  app = instance;
  hostContext = instance.getHostContext();
});
</script>

<main
  class="main"
  class:fullscreen={displayMode === "fullscreen"}
  class:card-state={isCardState}
  style:padding-top={hostContext?.safeAreaInsets?.top ? `${hostContext.safeAreaInsets.top}px` : undefined}
  style:padding-right={hostContext?.safeAreaInsets?.right ? `${hostContext.safeAreaInsets.right}px` : undefined}
  style:padding-bottom={hostContext?.safeAreaInsets?.bottom ? `${hostContext.safeAreaInsets.bottom}px` : undefined}
  style:padding-left={hostContext?.safeAreaInsets?.left ? `${hostContext.safeAreaInsets.left}px` : undefined}
>
  {#if !app}
    <div class="loading">Connecting...</div>
  {:else if viewerData && hasData && !error}
    <DocumentViewer {app} data={viewerData} {displayMode} />
  {:else if error}
    <div class="error-state">
      <h2>Error</h2>
      <p>{error}</p>
    </div>
  {:else}
    <EmptyState />
  {/if}
</main>

<style>
.main {
  width: 100%;
  min-height: 100%;
  padding: var(--spacing-sm, 0.5rem);
  display: flex;
  flex-direction: column;
  background: var(--color-background-primary);
  border-radius: var(--border-radius-lg, 10px);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
}

.main.card-state {
  justify-content: center;
  align-items: center;
}

.main.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  border-radius: 0;
  border: none;
  overflow: hidden;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.error-state {
  text-align: center;
  padding: var(--spacing-lg, 1.5rem);
  background: var(--color-background-secondary);
  border-radius: var(--border-radius-lg, 10px);
  border: 1px solid var(--color-border-primary);
}

.error-state h2 {
  margin: 0 0 var(--spacing-sm, 0.5rem) 0;
  font-size: 1.25rem;
  color: var(--color-error);
}

.error-state p {
  margin: var(--spacing-sm, 0.5rem) 0;
  color: var(--color-text-secondary);
}
</style>
