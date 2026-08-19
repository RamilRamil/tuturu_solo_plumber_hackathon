# Stream D report — frontend / wow-effect

Worktree: `.worktrees/frontend`  
Branch: `codex/frontend-wow`  
Not merged, not pushed.

## What shipped

- Ingredient menu with visible density labels; discrete radius 50/100/150; phase 1 without origin or prices.
- MapLibre map (hubs + POI) beside cards; pair card stays clickable below #5; UI does not re-sort `places[]`.
- Origin form locked until a **specific** `cluster_id` is selected; SSE uses that id, never `places[0]`.
- Incremental mock/live SSE (`resolved` → legs → hotels → breakdown → checkout → `done`) with ~3s to first leg.
- **Grey heuristic removed** from `startPrice`. Cards grey only from stream facts:
  - `warning.no_route` / `resolved.guard=misresolved` / `warning.not_sellable` / `missing_price` (incl. price `0` as absence).
  - Codes are not mixed.
  - `probe_status=not_sellable` still marks «дальше своим ходом» in phase 1; that is not post-origin routing grey.
- Unreachable cards stay in the list. Mock streams for Torzhok / Vladimir / Suzdal / Tver demonstrate the four reasons; unknown ids → HTTP 404 UI.
- Separate «почти подходит» (`AlmostFits`) for non-empty `coverage.missing`.
- Coverage panel from `/coverage.json` or `/mocks/coverage.json`; empty phase 1 outside loaded regions labeled as ingest hole.
- Share query: `encodeURIComponent` of the **whole** `cluster_id` (not a path segment) plus burger, radius, origin, dates, passengers. Restore on load. Copy button.
- Three hours states; null/empty `opening_hours` → `unknown`, not `closed`.
- Cache vs live source badges; `cache_fallback` timestamp on the backup burger; `fixture-confirmed` kept on breakdown.
- Loading / empty / error / retry / abort. Checkout URL rendered as-is. `0` RUB never shown as a fare.
- Production Vite/`Dockerfile` default API mode is `live` (`VITE_API_MODE_DEFAULT=live`); `vite` dev stays `mock`. Toggle remains.

## Build

```
npm run build   # tsc --noEmit && vite build
```

**PASS** in this worktree (`frontend/`). Chunk size warning only (MapLibre bundle).

## Remaining gaps

- Live `/api/price` against compose is not exercised here (no backend in this stream). Toggle is wired; G10 live pass still needs C up.
- Coverage hatch is a panel + legend, not a filled choropleth of Russia.
- Web hours lookup (F4) is out of 001 by spec.
- MapLibre chunk is large; no extra library was added to split it.
