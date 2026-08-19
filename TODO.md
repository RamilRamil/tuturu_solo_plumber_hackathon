# TODO.md

## Sprint 3h local MVP (2026-08-19)

## Honest re-probe (2026-08-19 evening)

### [orchestrator-integrator]

- [ ] Task 2 AFTER live D1/D2: if Uglich is sellable, drop on-foot from etalon v2; grey card only on a confirmed not_sellable hub. Do not brief B/C until then.
- Do not merge `codex/data` sidecar 29MB DB over live demo DB.
- Do not push. Do not deploy VPS.

### [codex-reprobe-d1d2]

- [ ] Live D1/D2 October 2026 for Uglich, Yaroslavl, Rostov Veliky, Moscow + 20 largest not_sellable by population
- [ ] Honest latency_ms and per-call checked_at/date_probed (no shared timestamp, no 1ms fake miss)
- [ ] Write leg.min_price on D2 (0 RUB = absent)
- [ ] D5 warmup for whatever Tutu returned + backup Yaroslavl; denser D4 ancient_temple if SPARQL allows
- Sole writer of `/Users/ramilmustafin/Projects/tuturu_hackaton/data/burger.db`. Never write `.worktrees/data/data/burger.db`.

### [codex-frontend-named-poi]

- [x] Render only named POIs on cards/map; counts stay honest over all objects
- Do not change etalon cluster_id, grey-card rules, or ingredients

### [codex-live-price]

- [ ] B3 first: is mcp.tutu.ru public or token? ENV only, never hardcode
- [ ] B1: resolve cluster from cluster_id + hub table; no 404 on empty cluster table
- [ ] B2: BURGER_LIVE_TUTU actually calls TutuMcp.call_tool; mock/cache path unchanged
- Do not edit cluster_places.py, api-contract.md, schema.sql, frontend/**

### [codex-frontend-ia]

- [ ] F1 short PlaceCards; objects only in PlaceDetails for selectedPlace; almost-fits top-5 + show more
- [ ] F2 origin+price next to map; PriceStream summary + Buy on Tutu
- [ ] F3 collapse IngredientMenu; preselect top-1; hover/selected
- [ ] F4 default etalon Uglich 2/2; do not glow density_measured<=1
- Do not edit types/contract.ts or api/*.ts; do not sort places[] (SC-D2)

### [orchestrator-integrator-archive]

- [x] Checkpoint `f45ffdc` + SQLite backup `data/backups/burger.db.checkpoint-3h`
- [x] G10: Python 3.12, tests, Docker Compose through nginx
- [x] Persist live discs into `cluster` so `/api/price` finds clicked `cluster_id`
- [x] Sequential merge `codex/price-live` and `codex/frontend-wow` into local `main`
- [ ] Sequential merge `codex/data` into local `main`
- [ ] Smoke, screenshots, README, final report
- Do not push. Do not deploy VPS.

### [codex-data]

- [ ] D4 Wikidata then D5 cache warmup on worktree copy of burger.db (sole writer)
- [ ] Honest `coverage.json` for useful CFD; NW only if time
- [ ] Commit only small JSON/summaries; never PBF or SQLite

### [codex-price-live]

- [ ] Live Tutu best-effort; keep `fixture-confirmed` until proven
- [ ] Guard, directed legs, return fallback, hotels stay_total, breakdown, checkout URL as-is
- [ ] Reconstruct cluster from `cluster_id` if `cluster` table empty

### [codex-frontend-wow]

- [ ] Desktop-first UX; inversion; SSE; grey from routing results; almost-fits; coverage; share URL

## Harden places (codex/harden-places)

### [places-perf-helper]

- [x] E. /api/places: hub_id POI index, hull diameter, persist ranked[:cap]
- [x] F. ingest/coverage_state.py union helper (do not wire parse_osm.py)
- Do not edit parse_osm.py, frontend/**, price.py, schema.sql, burger.db

## Readiness basket A

### [worker-a-ingest]

- [x] G5 Tutu concurrency 1/2/4/8 + raw JSON for Architect G9
- [x] G7 pyosmium + Yaroslavl oblast pbf counts vs field-test §12
- [x] G8 .db transfer path note (no second FastAPI)
- [x] G6 SSE smoke through nginx (`GET /_sse_smoke`, events one-by-one)
- [x] G10 hour-26 criterion in §6 pointer; §3 table is Architect
- [x] D1 wave1 hub probe (268, dM<=400)
- [x] D3 Yaroslavl oblast OSM POI (osmium, G7 pbf)
- [x] D2 sellable pairs <=150km with POI both sides
- [ ] D4 Wikidata enrich
- [ ] D5 etalon cache warmup
