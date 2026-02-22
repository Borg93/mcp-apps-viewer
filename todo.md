# Riksarkivet Document Viewer — TODO


## 4. Viewer Analytics & Custom Traces

Add lightweight client-side analytics that flow through the MCP tool bridge into Python logging / OTEL.

### 4.1 Analytics singleton (`ui/lib/analytics.ts` — new file)
- [ ] `initAnalytics(app)` — store app ref, start 30s flush interval, listen for `visibilitychange`
- [ ] `track(type, attrs?)` — push event to buffer (sync, never blocks)
- [ ] `flush()` — swap buffer, call `app.callServerTool("report-analytics", { events })`, fire-and-forget
- [ ] `destroyAnalytics()` — best-effort final flush, clear interval, remove listener
- [ ] Session ID via `crypto.randomUUID()`, generated once at module load
- [ ] Each event shape: `{ type, timestamp, session_id, ...attrs }`

### 4.2 Server-side `report-analytics` tool (`src/tools.py`)
- [ ] Add `report-analytics` tool with `visibility=["app"]` (invisible to LLM)
- [ ] Log each event as structured log record (`logger.info` with `extra=` dict)
- [ ] Events flow into existing Python logging → OTEL log bridge
- [ ] Return minimal "ok" text content

### 4.3 Instrument UI components
- [ ] `App.svelte` — init/destroy analytics, track `session_start` with `page_count`
- [ ] `DocumentContainer.svelte` — track `page_view` with `page_index`, `from_page`, `from_cache`
- [ ] `DocumentViewer.svelte` — track `text_click` with `page_index`, `line_id`
- [ ] `ThumbnailStrip.svelte` — track `thumbnail_navigate` with `target_page`

**Events summary:**
| Event | Component | Key attrs |
|---|---|---|
| `session_start` | App.svelte | page_count |
| `page_view` | DocumentContainer | page_index, from_page, from_cache |
| `text_click` | DocumentViewer | page_index, line_id |
| `thumbnail_navigate` | ThumbnailStrip | target_page |

---

## 5. Future Enhancements

- [ ] Confidence heatmap mode (color lines/words by OCR confidence)
- [ ] Search within transcription panel (find text, jump to matching line)
- [ ] Migrate UI to Bits UI + Tailwind CSS for consistent component library and utility-first styling
