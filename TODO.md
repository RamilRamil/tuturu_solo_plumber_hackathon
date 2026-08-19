# TODO.md

## Sprint 3h local MVP (2026-08-19)

### [orchestrator-integrator]

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
