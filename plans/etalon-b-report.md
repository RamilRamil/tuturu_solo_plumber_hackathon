# STREAM_REPORT — Worker B (etalon v2, phase-1 places)

Branch: `codex/etalon-b`
Worktree: `.worktrees/etalon-b`
Stop. Not merged. Not pushed.

## What changed

Tests only. Cluster ranking code, `w1..w6`, routers, fixtures, ingest, frontend, `price.py`, `schema.sql`, `lib/**` were not edited.

Etalon v2 honest card is single-hub Uglich from `fixtures/etalon_1.json`
(`cluster_id` there; tests load it, no Cyrillic literals in Python).
Coverage 2/2, hub `probe_status=not_sellable` (on-foot). Pair-in-top-5 is not a gate.

Yaroslavl+Rostov pair stays in `places[]` as almost-fits: `len(matched)==1`,
`industrial_museum` in `missing`. Id from `etalon_1.json` field `almost_fits_pair_id`.

SC-B2 backup single-hub Yaroslavl `ancient_temple+ruins` unchanged.
SC-B3 coverage monotonicity unchanged.

`test_hub_filtered_pois_find_etalon_pair`: etalon is one hub; hub-filtered POIs still yield full coverage.
`test_places_perf.py`: asserts the etalon id is a single hub (no comma in cluster_id), not a 2-hub pair.

No factories added to `industrial_museum`. Weights not tuned.

## Tests

From this worktree:

```
/Users/ramilmustafin/Projects/tuturu_hackaton/.venv/bin/python -m unittest tests.test_places tests.test_places_perf -v
```

17 tests OK.

Fixture bench print: `hubs=10, pois=6, candidates=12, ms~2, total_found=5`.

## Not touched

`backend/services/cluster_*.py`, `backend/routers/places.py`, `fixtures/**`, `ingest/**`, `frontend/**`, `backend/services/price.py`, `schema.sql`, `lib/**`.
