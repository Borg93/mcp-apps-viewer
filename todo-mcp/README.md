# todo-mcp

A todo app built with FastMCP 3.0 + Svelte 5 demonstrating MCP Apps (SEP-1865).
The LLM can create, add, check, and remove items through conversation.
The iframe persists across turns — no reload between messages.

## Structure

```
todo-mcp/
├── server.py          # FastMCP 3.0 server
├── requirements.txt
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.ts
        └── App.svelte
```

## Setup

### 1. Build the frontend

```bash
cd frontend
npm install
npm run build
# Produces frontend/dist/index.html (single self-contained file)
cd ..
```

### 2. Install Python deps

```bash
pip install -r requirements.txt
# or with uv:
uv pip install -r requirements.txt
```

### 3. Add to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todo-server": {
      "command": "python",
      "args": ["/absolute/path/to/todo-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. Then try:

- "Create a shopping list with milk, eggs, bread"
- "Add butter to the list"
- "Check off milk and eggs"
- "Remove bread"
- "What's still on the list?"

## How it works

1. LLM calls `update_todo` → server returns `structuredContent: {todos: [...]}`
2. Host sends `ui/notifications/tool-result` to the iframe
3. `ontoolresult` fires → `todos = data.todos` → Svelte re-renders
4. **Same iframe, every turn.** No reload.

## Known limitation

Checkbox clicks from the iframe call `toggle_item` via `callServerTool`.
This is broken in Claude Desktop today (bug #386 — Zod validation error).
The code falls back to an optimistic local update + `sendMessage` to inform the LLM.
It works fully in the `basic-host` test environment from the ext-apps repo.

## Test with basic-host (no Claude Desktop needed)

```bash
git clone https://github.com/modelcontextprotocol/ext-apps
cd ext-apps
npm install
# Follow their README to run basic-host, point it at server.py
```
