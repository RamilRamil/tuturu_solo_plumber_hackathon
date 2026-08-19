# STREAM_REPORT (harden-price)

Branch: `codex/harden-price` (worktree `.worktrees/harden-price`, from `ce9aa1e`).
Not merged to main. Not pushed. No SQLite written under `.worktrees/data`.

## A. Honest price_status

Overall `breakdown` / `done` `price_status` is `fixture-confirmed` unless
`BURGER_SC_PRICE_ACCEPTED` is truthy. That env is the only way overall status
may become `live`. One hop with `source: live` does not flip the overall field.
Per-leg / per-hotel `source` stays `live|cache`. Did not add `partial-live`.

## B. Route cache lookup

Lookup key is `(origin_hub, dest_hub, requested day, adults, pax_sig)`.
`leg.date_probed` is not used as the cache date. Exact miss: live if
`BURGER_LIVE_TUTU`, else last-resort `leg` row with warning `stale_leg` and
optional `stale: true` on the leg event. Live timeout/raise still uses
`cache_fallback` when a stale/cache quote is shown. Checkout URL and price
come from the same payload/date.

`search_multitransport` stays adults-only: non-empty `children_ages` emits
`child_fare_unverified` and still queries adults. `search_hotels` gets
`children_ages`. D5 warmup INSERT writes `adults` + empty `pax_sig` and
returns `attempted`, `succeeded`, `unique_rows`, `overwritten`, `errors`.

## C. Cluster row required

`load_cluster_row` 404s when table `cluster` has no row. Reconstruct-from-hubs
bypass is gone. Unknown id 404s before SSE. `POST /api/places` then
`/api/price` is 200. `make_cluster_id` format unchanged.

## D. Event loop

`POST /api/price` 404-checks on a short SQLite connection, then runs
`iter_price_events` on a worker thread. The async generator only waits on a
queue (`asyncio.to_thread`). SSE stays sequential. Demo 3s/1s pauses only if
`BURGER_PRICE_DEMO_PACE=1`. Client disconnect sets a cancel event and stops
further hops; MCP/DB close in `finally`.

## Recovered warning

Failed return hop + successful previous-city fallback emits `no_route` with
`"recovered": true`. Codes stay distinct:
`misresolved` / `not_sellable` / `no_route` / `no_price` / `cache_fallback` /
`stale_leg` / `child_fare_unverified`.

## Tests

Command (venv is not in this worktree):

```
cd .worktrees/harden-price
PYTHONPATH=. /Users/ramilmustafin/Projects/tuturu_hackaton/.venv/bin/python -m unittest tests.test_price tests.test_guard -v
```

Result: **28 passed, 1 skipped** (`test_live_tutu_network_optional` unless
`BURGER_LIVE_NET=1`).

New / replaced coverage:

- one live hop stays `fixture-confirmed`; leg `source` may be `live`
- October 2026 `route_cache` for adults=1 `pax_sig=''` on the requested day
  is what `/api/price` (live off) reads, not `leg.date_probed`
- `DELETE FROM cluster` then `POST /api/price` → HTTP 404
- `POST /api/places` then `/api/price` → 200
- return fallback warning has `recovered: true`
- `children_ages` emits `child_fare_unverified`
- slow hop (2s sleep) still lets `GET /healthz` return in under 1s on the
  same FastAPI app

## Remaining

- Retry of D5 warmup on MCP errors is later (writer is correct now).
- Frontend H must consume `recovered` / `stale` / `child_fare_unverified`
  (this stream did not edit frontend).
- SC-price still requires a human to set `BURGER_SC_PRICE_ACCEPTED` after
  both etalon #1 and backup live runs.
