# STREAM_REPORT — harden-places (places-perf-helper)

Branch: `codex/harden-places`
Worktree: `.worktrees/harden-places`
Stop. Not merged. Not pushed.
Did not write `burger.db` or `data/places_bench.json`.

## E. /api/places performance

- In-memory POI index by `hub_id`. Each candidate only sees POIs attached to those hubs, then `poi_in_discs` (`r_local` 25 km). Attach radius 50 km > `r_local`, so the disc is not silently shrunk for attached POIs. Full POI list is not scanned per candidate.
- Diameter: exact pairwise haversine if n<=40; else convex hull (Andrew monotone chain on local km projection) then pairwise haversine on hull vertices. Coverage ranking unchanged. Hull diameter matches full pairwise on a 50-point circle test.
- `persist_clusters`: `INSERT OR REPLACE` only when the row is missing or `hub_ids` / title / center changed. Persists `ranked[:limit]` plus any ranked `cluster_id` already stored for that `radius_km`.
- Semantics kept: discs, coverage-dominates ranking, `cluster_id`.

### Fixture bench (golden rows, not the live 8MB db)

Printed by `tests.test_places_perf.PlacesPerfTests.test_benchmark_golden_fixtures_prints_stats`:

```
{"hubs": 9, "pois": 5, "candidates": 11, "ms": 2.199, "total_found": 4}
```

Honest timing: 9 hubs / 5 POIs is not the live CFD. Target <200 ms on typical burgers is the goal after hub indexing + persist cap; live timing was not measured here (data agent is the sole `burger.db` writer).

## F. Union coverage helper

- New file `ingest/coverage_state.py`. ASCII literals. **Not wired** into `parse_osm.py`.
- Loads existing `coverage.json` if present. Merges wave regions into `regions` = `{slug, label, status: loaded|failed, poi_wave}`.
- Failed never becomes `loaded`. A failed wave does not drop previously loaded slugs.
- Slug is identity; label is display. No English/Russian substring matching.
- `poi_count_db` is passed in by the caller (DB COUNT). `poi_count_wave` is the current wave.
- Tests: wave A moscow + wave B tver => both loaded; failed wave does not drop previous or add as loaded.

## Tests

From this worktree:

```
.venv/bin/python -m unittest tests.test_places -v
.venv/bin/python -m unittest tests.test_places tests.test_places_perf tests.test_coverage_state -v
```

22 tests OK. Etalon pair still found via hub-filtered POIs on golden fixtures.

## Not touched

`ingest/parse_osm.py`, `frontend/**`, `backend/services/price.py`, `backend/routers/price.py`, `schema.sql`, `.worktrees/data/data/burger.db`.
