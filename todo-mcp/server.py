from fastmcp import FastMCP
from pathlib import Path
from typing import Literal

mcp = FastMCP("todo-server")

# In-memory state (one list per server process — fine for local testing)
todos: list[dict] = []

UI_URI = "ui://todo-server/app"
HTML_PATH = Path(__file__).parent / "frontend" / "dist" / "index.html"


# ── UI resource ────────────────────────────────────────────────────────────────
# Host fetches this once via resources/read and caches it.
# The HTML is the compiled Svelte app — all JS/CSS inlined, no external deps.

@mcp.resource(
    uri=UI_URI,
    mime_type="text/html;profile=mcp-app",
    _meta={"ui": {"prefersBorder": False}},
)
def todo_app_resource() -> str:
    if not HTML_PATH.exists():
        raise FileNotFoundError(
            f"Frontend not built. Run: cd frontend && npm install && npm run build"
        )
    return HTML_PATH.read_text()


# ── LLM-visible tool ───────────────────────────────────────────────────────────
# visibility defaults to ["model", "app"] — LLM calls this from conversation,
# iframe can also call it directly.

@mcp.tool(
    description=(
        "Create or update the todo list. "
        "Use action='create' with items=[...] to start a new list. "
        "Use action='add' with items=[...] to append. "
        "Use action='toggle' with item_id=<id> to check/uncheck. "
        "Use action='remove' with item_id=<id> to delete. "
        "Use action='clear' to wipe the list."
    ),
    _meta={
        "ui": {
            "resourceUri": UI_URI,
            "visibility": ["model", "app"],
        }
    },
)
def update_todo(
    action: Literal["create", "add", "toggle", "remove", "clear"],
    items: list[str] | None = None,
    item_id: str | None = None,
) -> dict:
    global todos

    if action == "create" and items is not None:
        todos = [{"id": str(i), "text": t, "done": False} for i, t in enumerate(items)]

    elif action == "add" and items is not None:
        existing_ids = {t["id"] for t in todos}
        for text in items:
            new_id = str(len(todos) + len(text))  # simple unique id
            while new_id in existing_ids:
                new_id += "_"
            todos.append({"id": new_id, "text": text, "done": False})

    elif action == "toggle" and item_id is not None:
        for t in todos:
            if t["id"] == item_id:
                t["done"] = not t["done"]

    elif action == "remove" and item_id is not None:
        todos = [t for t in todos if t["id"] != item_id]

    elif action == "clear":
        todos = []

    pending = [t["text"] for t in todos if not t["done"]]
    done_items = [t["text"] for t in todos if t["done"]]

    return {
        # content[] → goes into LLM context so it can answer "what's left?"
        "content": [{
            "type": "text",
            "text": (
                f"Todo list ({len(todos)} items):\n"
                f"  Pending ({len(pending)}): {', '.join(pending) or 'none'}\n"
                f"  Done ({len(done_items)}): {', '.join(done_items) or 'none'}"
            ),
        }],
        # structuredContent → iframe only, never touches LLM context
        "structuredContent": {"todos": todos},
    }


# ── App-only tool ──────────────────────────────────────────────────────────────
# visibility: ["app"] — hidden from LLM's tools/list.
# Only callable from the iframe via callServerTool().
# NOTE: broken in Claude Desktop today (bug #386). Works in basic-host.

@mcp.tool(
    description="Toggle a todo item done/undone (called from UI only)",
    _meta={
        "ui": {
            "resourceUri": UI_URI,
            "visibility": ["app"],
        }
    },
)
def toggle_item(item_id: str) -> dict:
    global todos
    for t in todos:
        if t["id"] == item_id:
            t["done"] = not t["done"]

    pending = [t["text"] for t in todos if not t["done"]]
    done_items = [t["text"] for t in todos if t["done"]]

    return {
        "content": [{"type": "text", "text": "toggled"}],
        "structuredContent": {"todos": todos},
    }


if __name__ == "__main__":
    mcp.run()
