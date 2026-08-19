# Stream C / live pricing report

Branch: `codex/price-live` (worktree `.worktrees/price`). Not merged to main. Not pushed.

## Live Tutu

**Confirmed (one directed search hop), not a full SC-price run.**

A real `search_multitransport` against `https://mcp.tutu.ru/mcp` (timeout 30s, search only, no booking) for origin Moscow / dest Yaroslavl / date `2026-10-09` / 1 adult returned:

- `meta.to` resolved to Yaroslavl in Yaroslavl oblast (guard region would pass)
- non-absent price: **1035 RUB** (bus)
- `checkout_url` present (host `mtp-deeplink.tutu.ru`, passed through as-is; URL not copied here)

Default product `PRICE_STATUS` stays `fixture-confirmed` until `/api/price` itself gets at least one live-priced hop (`BURGER_LIVE_TUTU=1`). `done.price_status` becomes `live` only in that case.

Not confirmed live in this stream:

- full SSE `/api/price` with `BURGER_LIVE_TUTU=1` against the app DB
- backup single-hub burger
- return hop / hotel `search_hotels`

## Checkout URL

**Obtained** on the live hop above. Product code never rebuilds or mutates the string; it copies `checkout_url` from the offer/cache payload.

Fixture path still has no checkout URLs in golden `leg` / `hotel_cache` rows, so G10 fixture SSE may omit the `checkout` event.

## Tests

Command (venv Python, worktree cwd):

`python -m unittest tests.test_price -v`

Result: **15 passed, 1 skipped** (`test_live_tutu_network_optional` unless `BURGER_LIVE_NET=1`).

Also: `python -m unittest tests.test_guard -v` → **8 passed** (lib/tutu_mcp not edited).

Covered without network:

- reconstruct hubs from `cluster_id` after `DELETE FROM cluster`
- 0 RUB is absence; live 0 falls back to cache and is never shown as a fare
- live disabled → cache, `fixture-confirmed`
- live timeout/raise → `cache_fallback` + cache prices
- mocked live priced hop may set `price_status=live` and pass checkout URL through

## Remaining risks

- SC-price (etalon #1 **and** backup, ±15% vs 4342) is still open; one live hop is not both scenarios.
- Checkout links expire (R3); do not rebuild them, refresh by searching again before demo.
- `probe_destination` still reads `offers`; live Tutu returns `variants`. Price worker parses both so a live hop can be priced without duplicating the guard.
- Reconstruct requires every parsed hub to exist in table `hub`. Unknown id → HTTP 404 before SSE.
- Partial live failures keep streaming; `done.ok` stays true if some legs priced.
- Concurrency cap 4 and timeout 30s remain in `lib.tutu_mcp` (`MAX_CONCURRENCY`, `CALL_TIMEOUT_S`).
