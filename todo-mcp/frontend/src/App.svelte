<script lang="ts">
  import { App } from "@modelcontextprotocol/ext-apps";

  type Todo = { id: string; text: string; done: boolean };

  let todos = $state<Todo[]>([]);
  let app = $state<App | null>(null);
  let connected = $state(false);
  let error = $state<string | null>(null);
  let newText = $state("");

  $effect(() => {
    const instance = new App({ name: "Todo App", version: "1.0.0" });

    // Fires for every tool call — both LLM-initiated and UI-initiated.
    // This is the only update path. No other state management needed.
    instance.ontoolresult = (result) => {
      const data = result.structuredContent as { todos: Todo[] } | null;
      if (!data?.todos) return;

      todos = data.todos;

      // Keep LLM in sync after UI-initiated changes (e.g. checkbox clicks).
      // Without this, "what's left?" after a checkbox click gives stale answers.
      const pending = todos.filter((t) => !t.done).map((t) => t.text);
      const done = todos.filter((t) => t.done).map((t) => t.text);
      instance.updateModelContext({
        content: [{
          type: "text",
          text: `Todo state — Pending: ${pending.join(", ") || "none"} | Done: ${done.join(", ") || "none"}`,
        }],
      });
    };

    instance
      .connect()
      .then(() => {
        connected = true;
        app = instance;
      })
      .catch((e: Error) => {
        error = e.message;
      });

    return () => instance.close();
  });

  // Checkbox clicked directly in the UI.
  // Calls the app-only toggle_item tool (hidden from LLM).
  // Falls back to calling update_todo if toggle_item is rejected (Claude Desktop bug #386).
  async function handleCheckbox(id: string) {
    if (!app) return;
    try {
      await app.callServerTool({ name: "toggle_item", arguments: { item_id: id } });
    } catch {
      // Fallback for Claude Desktop bug #386 — callServerTool broken
      // Optimistic local update so the UI feels instant
      todos = todos.map((t) => t.id === id ? { ...t, done: !t.done } : t);
      // Tell the LLM so it stays in sync
      await app.sendMessage({
        role: "user",
        content: [{ type: "text", text: `I toggled "${todos.find((t) => t.id === id)?.text}"` }],
      });
    }
  }

  // User types in the input box and presses Enter or clicks Add.
  // Calls update_todo directly — silent to LLM (no chat message added).
  async function handleAdd() {
    if (!app || !newText.trim()) return;
    const text = newText.trim();
    newText = "";
    await app.callServerTool({
      name: "update_todo",
      arguments: { action: "add", items: [text] },
    });
  }
</script>

<div class="app">
  {#if error}
    <p class="error">Connection error: {error}</p>
  {:else if !connected}
    <p class="connecting">Connecting…</p>
  {:else if todos.length === 0}
    <p class="empty">No items yet. Ask me to create a list!</p>
  {:else}
    <ul>
      {#each todos as todo (todo.id)}
        <li class:done={todo.done}>
          <label>
            <input
              type="checkbox"
              checked={todo.done}
              onchange={() => handleCheckbox(todo.id)}
            />
            <span>{todo.text}</span>
          </label>
        </li>
      {/each}
    </ul>
  {/if}

  {#if connected}
    <div class="add-row">
      <input
        type="text"
        placeholder="Add item…"
        bind:value={newText}
        onkeydown={(e) => e.key === "Enter" && handleAdd()}
      />
      <button onclick={handleAdd} disabled={!newText.trim()}>Add</button>
    </div>
  {/if}
</div>

<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  .app {
    font-family: system-ui, sans-serif;
    padding: 1rem;
    max-width: 400px;
    color: var(--color-text-primary, #111);
    background: var(--color-background-primary, #fff);
    min-height: 100dvh;
  }

  ul { list-style: none; margin-bottom: 1rem; }

  li {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border-primary, #eee);
  }

  label {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    cursor: pointer;
  }

  input[type="checkbox"] { width: 1rem; height: 1rem; flex-shrink: 0; cursor: pointer; }

  .done span { text-decoration: line-through; opacity: 0.45; }

  .add-row {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .add-row input {
    flex: 1;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--color-border-primary, #ccc);
    border-radius: var(--border-radius-sm, 4px);
    font-size: 0.9rem;
    background: var(--color-background-secondary, #fafafa);
    color: var(--color-text-primary, #111);
  }

  .add-row button {
    padding: 0.4rem 0.9rem;
    background: var(--color-text-primary, #111);
    color: var(--color-background-primary, #fff);
    border: none;
    border-radius: var(--border-radius-sm, 4px);
    cursor: pointer;
    font-size: 0.9rem;
  }

  .add-row button:disabled { opacity: 0.35; cursor: default; }

  .empty, .connecting { color: var(--color-text-secondary, #888); font-size: 0.9rem; }
  .error { color: red; font-size: 0.85rem; }
</style>
