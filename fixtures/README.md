# Golden fixtures (G9)

Format of `rows/*.json` = columns that `lib/tutu_mcp.py` / `lib/models.py` write to SQLite
(`schema.sql`). Wrappers may add `provenance` / `source`; the loader strips those keys
before INSERT.

**Provenance:** Worker A dumped live G5 JSON under `fixtures/raw/` (host `local-mac-not-vps`, 2026-08-19).
`rows/mcp_cache.json` stores those envelopes as `lib/tutu_mcp.py` would write `mcp_cache`.
Etalon v2 (live shape): Yaroslavl has **no** `industrial_museum`. The only live industrial_museum is Uglich "Syr Kult Prosvet". Pair Yaroslavl+Rostov is coverage 1/2 (almost-fits). Do not re-add factory POIs.

Etalon total 4342 RUB remains **fixture-confirmed** (field-test §8), **not** SC-price.
G3 node (Borisoglebsky) has no live Tutu dump; marked fixture-confirmed.

Drop additional raw files here; Architect can refresh `mcp_cache` without changing `schema.sql`.

| file | what |
|---|---|
| `tutu/rostov.json` | query Rostov -> Rostov-on-Don (guard RED) |
| `tutu/rostov_veliky.json` | query Rostov Veliky (guard GREEN) |
| `tutu/veliky_novgorod.json` | query Veliky Novgorod -> Saint Petersburg |
| `g3_outside_handbook.json` | Borisoglebsky, not in cities_ru (G3) |
| `rows/hubs.json` | hub table |
| `rows/poi.json` | Yaroslavl oblast POI sample |
| `rows/legs.json` | directed legs including etalon + Torzhok asymmetry |
| `rows/hotel_cache.json` | hotel stay_total |
| `rows/clusters.json` | etalon #1 + backup single-hub (B4) |
| `rows/mcp_cache.json` | mcp_cache as the lib writes it |
| `rows/misresolve_log.json` | B1 samples |
| `etalon_1.json` | etalon v2 Uglich on-foot bundle; price_status=fixture-confirmed |
| `backup_single_hub.json` | B4 backup burger |
