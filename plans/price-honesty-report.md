# Stream C / price honesty report

Branch: `codex/price-honesty` (worktree `.worktrees/price-honesty`, from main `611d886` with merged `codex/live-price`).
Not merged. Not pushed. Search only; never book/pay.
`lib/tutu_mcp.py` unchanged (P4 uses existing `call_tool`). No Authorization header added.

Python: `/Users/ramilmustafin/Projects/tuturu_hackaton/.venv/bin/python`

Live-price B1/B2/B3 history: commit `9f4f1a4` / `plans/price-live-report.md`.

## P1 - overall `price_status` from emitted sources

`overall_price_status(sources, live_on)` reads hop/hotel `source` after they are emitted.
It is not an env lookup. `BURGER_SC_PRICE_ACCEPTED` stays on `/healthz` and boot only.

| priced sources | `BURGER_LIVE_TUTU` | overall |
|---|---|---|
| all `live` | any | `live` |
| mix live + cache | any | `mixed` |
| all `cache` | on | `cache` |
| all `cache` | off | `fixture` |
| none | on | `cache` (never `live`) |
| none | off | `fixture` |

Old token `fixture-confirmed` is not emitted.

## P2 remainder - visible `cache_fallback`

When live search raises (network/HTTP/parse) and a cache quote exists:
- still emit the cache quote with `source=cache`
- SSE `warning` `code=cache_fallback` with `message` like `live search failed (TimeoutError)`
- live off does not emit fake live-error warnings

## P4 - `create_checkout_link`

For the chosen priced offer (same as the `leg`/`hotel` price), if `checkout_url` is missing and `checkout_ref` is a non-empty dict, one `call_tool("create_checkout_link", args)` with opaque ref fields. Avia also gets `passengers_full` / `child` / `infant` when those keys are absent. Returned `checkout_url` is copied into SSE `checkout` exactly. Tool failure skips that item only. Existing URL on hotels/etrain is kept. `mcp_cache` inside `TutuMcp` is the only cache.

## P3 - ops flags (orchestrator after merge; not deployed here)

Demo needs `BURGER_LIVE_TUTU=1`. Optional `BURGER_PRICE_DEMO_PACE`. Warm up `mcp_cache` on the etalon so the demo is not 3-27s. `BURGER_SC_PRICE_ACCEPTED` is **not** required for the label `live`.

Did not SSH, edit parent `.env`, or change VPS / docker-compose.

## Tests

`PYTHONPATH=. python -m unittest tests.test_price tests.test_guard -v`

**33 passed, 1 skipped** (`test_live_tutu_network_optional` without `BURGER_LIVE_NET`).

- all hop sources live + `BURGER_SC_PRICE_ACCEPTED` unset -> overall `live`
- one live + one cache -> `mixed`
- live flag off -> `fixture` (even if `BURGER_SC_PRICE_ACCEPTED=1`)
- live raise -> `cache_fallback` message is more than the bare code
- `create_checkout_link` mocked when ref present and URL missing; SSE URL equals tool return
- empty `cluster` table still 200 SSE; unknown id 404 before SSE
- B1 guard / 0 RUB absence / per-item `source` live|cache unchanged
