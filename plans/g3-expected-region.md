# G3 freeze: expected_region for nodes outside cities_ru

Decision (orchestrator draft **frozen**, not rejected).

Rostov Veliky **is in** `data/cities_ru.json` as `name=Rostov`, `subject=Yaroslavl oblast`.
The etalon failure mode is a **query name** ("Rostov" → Rostov-on-Don), covered by B1 aliases.
Do not invent a second region source for that etalon.

The hour-0 problem is the **general case**: D3 finds a sellable OSM place that is **not** one of the 1134 handbook cities. Guard still needs `expected_region`.

## Frozen rules

1. **Handbook hit** (`name`+`subject` in `cities_ru.json`, or unique `name` with matching coords):
   - `expected_region = cities_ru.subject`
   - `expected_region_source = cities_ru.subject`
   - This is canonical against OSM `admin_level=4`.

2. **Handbook miss** (OSM place used as a hub / guard subject, not in the 1134 list):
   - `expected_region = name:ru` of the OSM `admin_level=4` polygon containing the point (point-in-polygon). If `name:ru` is empty, use `name`.
   - `expected_region_source = osm.admin_level_4`

3. **No polygon**:
   - `expected_region` is NULL, `expected_region_source = missing`
   - `probe_status = misresolved`
   - **Do not delete** the hub. It stays for "on your own" / later retry.

4. **Mismatch when the handbook row exists**:
   - Subject wins. OSM `admin_level=4` is written to `misresolve_log` only
     (`expected_region_source` stays `cities_ru.subject`; log note `osm_subject_mismatch`).
   - OSM does not override the handbook.

Implemented in `lib/tutu_mcp.py` as `resolve_expected_region`. Guard remains `check_resolve` (region substring after normalize).

## G3 fixture (not Rostov Veliky)

`fixtures/g3_outside_handbook.json`: settlement Borisoglebsky (Yaroslavl oblast), absent from `cities_ru.json`. Region must come from OSM admin_level=4. Guard green when Tutu `meta.to.region` contains that subject.
