# STREAM_REPORT — data worker (`codex/data`)

Worktree: `/Users/ramilmustafin/Projects/tuturu_hackaton/.worktrees/data`
Branch: `codex/data` (not merged, not pushed).
Sole SQLite: `.worktrees/data/data/burger.db` (not committed).

## D4 Wikidata

Status: **done** (ran before D5 on Yaroslavl-only POI, then re-ran after CFD D3).

Final counts on the worktree db:

| metric | value |
|---|---|
| poi | 45140 |
| matched OSM wikidata tag | 1362 |
| matched ~100 m coord | 5914 |
| P571 inception filled this run | 3040 |
| with_date | 7881 (17.46%) |
| with_wikidata | 7587 |
| with_wikipedia | 792 |
| significance avg / max / ge5 | 2.2798 / 10.0 / 7531 |
| year buckets | &lt;1500: 123; 1500-1699: 718; 1700-1899: 4702; 1900+: 2338 |
| industrial_museum | 49 OSM rows (13 wikidata, 11 dated) — **not faked** |

SPARQL boxed to Central FD (`31-48E, 49.5-61N`). Classes: Q16970, Q44613, Q23413, Q57831, Q879050, Q16560.

Failures (non-fatal):

- query.wikidata.org HTTP 502 / timeout on subclass query for Q16970; P31 fallback returned rows.
- wbgetentities HTTP 429 on OSM-tag batches after CFD expand; SPARQL + coord match still filled dates/Q-ids.

Summary file: `data/d4_summary.json`.

## D5 cache warmup

Status: **done**. Tools: `search_multitransport`, `search_hotels` only. No book / pay / order.

| metric | value |
|---|---|
| route_cache writes | 95 / 96 |
| hotel_cache writes | 64 / 64 |
| unique route_cache rows | 48 (PK is origin, dest, date — adults overwrite) |
| unique hotel_cache rows | 64 |
| skipped etalons | 0 |
| concurrency cap | 4 |
| timeout | 30s |

One live timeout: `search_multitransport` Moscow → Yaroslavl on 2026-10-02. Same (origin, dest, date) was written later for the 2-adult pass, so the unique key is present.

Summary file: `data/d5_summary.json`.

## Geographic coverage (D3)

Status: **all Central Federal District regional extracts loaded**. `russia-latest` was not downloaded.

`data/coverage.json` `regions_loaded` (honest list):

1. Moscow
2. Moscow oblast
3. Yaroslavl oblast
4. Vladimir oblast
5. Tver oblast
6. Ryazan oblast
7. Tula oblast
8. Kaluga oblast
9. Ivanovo oblast
10. Kostroma oblast
11. Belgorod oblast
12. Bryansk oblast
13. Voronezh oblast
14. Kursk oblast
15. Lipetsk oblast
16. Oryol oblast
17. Smolensk oblast
18. Tambov oblast

`regions_failed`: []. POI upserted: **45140**. Attached to a hub: 41789. Hubs 268→268, legs 433→433 (not wiped).

Empty results **outside** this list are an ingest hole, not “no interesting places”.

Etalon honesty (live OSM, Yaroslavl oblast):

- `industrial_museum` on Yaroslavl / Rostov Veliky hubs: **0**.
- Only oblast hit remains Uglich “Сыр Культ Просвет”.
- Yaroslavl `ancient_temple` 122, `ruins` 10 — backup single-hub burger still has ingredients.
- Golden `fixtures/` not replaced.

`admin_level_4` in coverage.json still includes mis-tagged rivers/boundaries from OSM; do not treat that array as the loaded-region list. Use `regions_loaded` / `regions_loaded_slugs`.

## DB (not committed)

- Path: `/Users/ramilmustafin/Projects/tuturu_hackaton/.worktrees/data/data/burger.db`
- Size: **29M** (was 4.0M at checkpoint f45ffdc)
- Checkpoint copy: `data/backups/burger.db.checkpoint-3h` (untracked, do not commit)

## Reproduce (from this worktree)

Python 3.12 via uv. Package `osmium` (not pyosmium). Network needed for Wikidata, Tutu MCP, and PBF downloads.

```bash
cd /Users/ramilmustafin/Projects/tuturu_hackaton/.worktrees/data

uv run --python 3.12 python ingest/enrich_wikidata.py --db data/burger.db
uv run --python 3.12 python ingest/warmup_cache.py --db data/burger.db
uv run --python 3.12 --with osmium python ingest/parse_osm.py --db data/burger.db --wave cfd
uv run --python 3.12 python ingest/enrich_wikidata.py --db data/burger.db
```

Waves: `--wave core` (moscow + moscow_oblast + yaroslavl_oblast), `priority_a` (core + neighbors), `cfd` (all 18 above), `cfd_rest`, `nwfd`.

PBF source: `https://download.openstreetmap.fr/extracts/russia/central_federal_district/*-latest.osm.pbf` (cached under `data/osm/`, gitignored).

## Cut for time

- **Northwestern FD** (`--wave nwfd`): not ingested. Novgorod / Leningrad / SPb / Pskov / Vologda remain an ingest hole.
- No D2 re-probe of new CFD pairs (out of this worker’s sequential MUST-DO; legs table left as wave-1 433 rows).
- No second D5 pass after geography expand (etalon windows already warm).

## Failures / notes

- First D4 SQLite write from a sandboxed run looked empty to a sandboxed reader; re-ran D4 with unsandboxed IO and WAL checkpoint. Integrator must copy **this** worktree db, not `tuturu_hackaton/data/burger.db`.
- Duplicate `parse_osm.py --wave cfd` process was killed; one parser finished.
- `industrial_museum` count 1 → 49 is Moscow/CFD OSM, not Yaroslavl/Rostov etalon pair. Do not treat that as etalon pair coverage.
