# STREAM_REPORT (Worker C / live-price)

Branch: `codex/live-price` (worktree `.worktrees/live-price`, from `dd03e06`).
Not merged. Not pushed. Did not set `BURGER_SC_PRICE_ACCEPTED`.
Overall `price_status` stays `fixture-confirmed`. Search only; never book/pay.

Python: `/Users/ramilmustafin/Projects/tuturu_hackaton/.venv/bin/python`

## B3 — MCP public, no token

Live POST to `https://mcp.tutu.ru/mcp` with only `Content-Type` and `Accept`
(no `Authorization`):

- `initialize` → HTTP 200, `serverInfo.name=tutu-mcp-server`
- `tools/call` `search_multitransport` (Moscow → Yaroslavl, `2026-10-09`,
  1 adult, `page_size=1`) → HTTP 200, priced bus offer (1035 RUB)

Matches Worker C live search (`plans/etalon-c-report.md`) and
`tutu-mcp-reference.md` §7 (no session header). Endpoint is public search.

**No `Authorization` header added. No `TUTU_MCP_TOKEN`. `.env.example` unchanged.**
Empty-token error path is not needed. Comment in `lib/tutu_mcp.py::_post`
records the decision so a second client is not invented.

## B1 — `/api/price` does not need table `cluster`

`load_cluster_row` / `resolve_cluster_hubs` parse `cluster_id` via
`parse_cluster_id_hubs`, then load those rows from table `hub`.
Table `cluster` is not queried. Missing hub → `UnknownCluster` reason
`unknown hub`. Illegal id → `illegal cluster_id`. Router HTTP 404 detail
is that reason, before SSE.

Live `data/burger.db` (parent tree): 268 hubs, 93 cluster rows. Etalon
`cluster_id` still resolves from hub even if cluster were empty.

Tests (`PYTHONPATH=. python -m unittest tests.test_price tests.test_guard -v`):

- **31 passed, 1 skipped** (`test_live_tutu_network_optional` without
  `BURGER_LIVE_NET=1`)
- `test_empty_cluster_table_still_prices`: `DELETE FROM cluster`, POST
  `/api/price` for etalon Uglich and backup Yaroslavl → HTTP 200 SSE
  (`resolved` … `done`), not 404
- `test_unknown_cluster_is_http_404_not_sse`: `c:no-such-hub` → 404
  `unknown hub` before SSE
- `test_illegal_cluster_id_is_http_404_before_sse`: `not-a-cluster` → 404
  `illegal cluster_id` before SSE
- `load_golden_fixtures` path still green

Did not persist table `cluster` from `/api/places`. Did not call Tutu from places.

## B2 — live `call_tool` actually fires

When `BURGER_LIVE_TUTU=1`, `quote_directed_hop` calls `live_hop_quote` →
`TutuMcp.probe_destination` → `TutuMcp.call_tool("search_multitransport")`
**before** `route_cache`. Hotel path already called `search_hotels` first.
Cache for live calls is `mcp_cache` inside `TutuMcp` (not a second cache).

When `BURGER_LIVE_TUTU=0`, still `route_cache` / `hotel_cache` / `leg` fixtures.

`test_live_on_calls_tool_despite_route_cache`: seeded `route_cache` (10 RUB)
does not skip live; mocked `call_tool` ran (`calls.n > 0`), legs `source=live`.

Guard `check_resolve` still runs before a dest is treated as priced.
0 RUB = `price_is_absent`. Three probe outcomes unchanged.

### Optional live probe (search only)

One `TutuMcp.call_tool("search_multitransport")` against parent
`data/burger.db` (not the empty worktree copy): Moscow → Uglich,
`2026-10-09`, 1 adult.

- `call_tool` ran
- `mcp_cache` **862 → 863** (delta +1; that args_hash was a miss)
- First variant: railway 1341.2 RUB (no checkout URL copied here)
- ASCII destination `Uglich` came back as `meta.to.name` Yaroslavl with
  empty region — product SSE still uses hub names + guard, not this ASCII probe

Did not run D5 warmup. Did not book.

## Remaining

- Live Uglich SSE still needs hub-name queries + guard; ASCII `Uglich` is
  not the product query.
- SC-price still gated on `BURGER_SC_PRICE_ACCEPTED` (unset).
- `route_cache` on the live DB remains the mock/offline path.
