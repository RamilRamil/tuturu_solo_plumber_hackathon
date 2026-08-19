# STREAM_REPORT (Worker C / price-honesty)

Branch: `codex/price-honesty` (worktree `.worktrees/price-honesty`).
Not merged. Not pushed.

Full report: `plans/price-honesty-report.md`

Prior live-price (B1 hub resolve, B2 live call_tool, B3 no Authorization):
`plans/price-live-report.md` and git `9f4f1a4`.

P1: overall `price_status` is `live` / `mixed` / `cache` / `fixture` from emitted hop/hotel sources. `BURGER_SC_PRICE_ACCEPTED` does not choose the word.
P2: `cache_fallback` warning message includes `live search failed (<ExceptionType>)`.
P4: `create_checkout_link` via existing `TutuMcp.call_tool` when `checkout_ref` is present and `checkout_url` is missing. URL copied as-is.

P3 ops (orchestrator after merge): demo needs `BURGER_LIVE_TUTU=1`; optional `BURGER_PRICE_DEMO_PACE`; warmup `mcp_cache` on etalon; `BURGER_SC_PRICE_ACCEPTED` is not required for label `live`.
