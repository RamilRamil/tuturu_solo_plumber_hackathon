# Stream D report - etalon v2 frontend

Worktree: `.worktrees/etalon-d`  
Branch: `codex/etalon-d-frontend`  
Not merged, not pushed.

## What shipped

- Etalon cluster is Uglich (`c:Углич|Ярославская область`). Old Yaroslavl+Rostov id kept as `ALMOST_FITS_PAIR_ID`.
- Default burger still `ancient_temple` + `industrial_museum`. No auto-select of a sellable pair; origin form stays locked until a cluster from the current `places[]` is chosen.
- Mock `places-etalon.json`: Uglich first, full coverage 2/2, `probe_status=not_sellable` (Smolensk church + Syr Kult Prosvet). Pair Yaroslavl+Rostov is coverage 1/2, missing `industrial_museum`, shown in «почти подходит», not hidden. Honest single Yaroslavl is also 1/2.
- On-foot cards are first-class: badge and copy «дальше своим ходом» + reason, full opacity, still clickable. They are not washed-out grey leftovers.
- Mock SSE for Uglich: `resolved` + warnings `no_route` / `not_sellable` + `done`. No fake 0 RUB tickets, no fake transport total. Incomplete breakdown is labeled as no ticket / on foot. Backup Yaroslavl and the pair still stream priced legs.
- UI copy is product language (coverage 1/2, missing museum, on-foot reason). No SC-D2 / G10 developer notes.

## Build

```
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
cd frontend && npm run build
```

**PASS** (`tsc --noEmit && vite build`). MapLibre chunk-size warning only.

## Remaining

- Live `/api/places` and `/api/price` against compose are not exercised in this stream.
- Coverage panel is still a list + legend, not a choropleth of Russia.
