# STREAM_REPORT — Worker A ingest D5 (etalon v2)

Branch: `codex/etalon-a-d5` (worktree `.worktrees/etalon-a`).
Not merged. Not pushed. Did not open `.worktrees/data/data/burger.db` for write.
Did not start a second OSM parse.

## DB

- Path: `/Users/ramilmustafin/Projects/tuturu_hackaton/data/burger.db`
- Size: **5 382 144 bytes** (~5.13 MiB); WAL/SHM 0 after warmup
- Counts after D5: hub **268**, poi **2084**, leg **433**, `route_cache` **32**, `hotel_cache` **16**

## D5 warmup (Oct 2026 windows 2/9/16/23, adults 1 and 2, `pax_sig=""`)

Concurrency 4. Timeout 30 s with 3 retries. Tools: `search_multitransport`, `search_hotels` only. No book/pay/order.

| metric | value |
|---|---|
| attempted | 48 |
| succeeded | 48 |
| unique_rows | 48 |
| overwritten | 0 |
| errors | 0 |
| empty_skipped | 0 |

Written: 16 Moscow↔Yaroslavl routes + 16 Moscow↔Uglich routes + 8 Yaroslavl hotels + 8 Uglich hotels.

Backup single-hub burger uses the same Moscow↔Yaroslavl tickets and Yaroslavl hotels (no extra keys).

Hotel `stay_total` (not nights×rate). After a shape rewrite, `/api/price` can read `hotels[0].min_price` / `stay.stay_total`. Cheapest live stay_total seen: Yaroslavl **750**, Uglich **689**. Demo window 2026-10-09 adults=1 Yaroslavl hotel is **750** (matches old golden).

## Honest Moscow↔Uglich

D1 `leg` Moscow→Uglich stays **`no_route`** (date_probed 2026-09-09). Status was **not** flipped to `ok`.

Live Oct 2026 `search_multitransport` nevertheless returned railway variants (sample min **1341.2** RUB) and reverse also had bus. Stored as-is; prices were not invented. `/api/price` exact `route_cache` hit may therefore show a ticket even while the D1 edge is grey. Product should treat cache vs `leg.status` explicitly.

## `leg.min_price` fill (ok only)

| hop | min_price | status left |
|---|---|---|
| Moscow → Yaroslavl | 1035 | ok |
| Yaroslavl → Rostov | 659 | ok |
| Rostov → Yaroslavl | 659 | ok |

Still **236** ok legs with NULL `min_price`. `no_route` rows untouched.

## D4 (time leftover)

`ingest/enrich_wikidata.py --ingredient ancient_temple` with Yaroslavl-oblast bbox against the **main** live DB. Wikidata SPARQL returned HTTP **429** (1 req/min outage rule). No POI rows updated. Summary: `data/d4_ancient_temple_summary.json`.

## Commits (this branch)

Code: `ingest/warmup_cache.py`, `ingest/enrich_wikidata.py`.
JSON: `data/d5_uglich_summary.json`, `data/d4_ancient_temple_summary.json`.
This file. No `*.db` / WAL / SHM / PBF.
