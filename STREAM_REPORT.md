# STREAM_REPORT (Worker D, R3-R5)

Branch: `codex/frontend-r345`
Worktree: `.worktrees/frontend-r345`

## What changed

### R3 Map framing and aspect
- `ClusterMap` frames the selected cluster with `fitBounds` over hubs plus named POIs (`isNamedPoi`), padding 56px, `maxZoom` 11.
- One real point uses `flyTo` at zoom 10 (not 8.2, not street-level).
- Zero points keep the previous camera.
- `ResizeObserver` on the map container calls `map.resize()` then `fitBounds`/`flyTo` so the view survives `.stage.has-selection` layout changes.
- `.stage.has-selection` mid column is wider; selected `.map` uses `aspect-ratio: 4 / 3` + `width: 100%` + `height: auto` (mobile 320px height kept).
- OpenFreeMap style URL unchanged. Marker colors/layers unchanged.

### R4 Human number formatting
- New helper `frontend/src/format.ts`: `formatKm` rounds OUR diameter to 1 decimal and drops trailing `.0` (`26.983` -> `27`).
- Tutu amounts (`leg.price`, `hotel.min_price`, `breakdown.total/transport/lodging`) are shown as received: no `Math.round` / `toFixed`. `formatMoney` only adds ASCII space thousands grouping on the integer part (`1341` -> `1 341`); a rare float keeps its fractional digits.
- `PlaceDetails` has no floats; left as-is. Coordinates are not printed in the UI.

### R5 Live only
- Removed `ModeToggle` and `mode` / `defaultApiMode` / `VITE_API_MODE_DEFAULT` usage.
- `fetchPlaces` / `streamPrice` / `fetchCoverage` always hit live APIs.
- Coverage still falls back to `/mocks/coverage.json` when `/api/coverage` fails.
- Deleted mock price stream, `fetchMockPlaces`, etalon/backup JSON.
- Moved `HttpError` to `frontend/src/api/price.ts`.
- SSE `source=live|cache` marks (`sourceMark`, `src-live`/`src-cache`, cache-stamp copy) kept.

## Files
- edited: `frontend/src/components/ClusterMap.tsx`, `frontend/src/styles.css`, `frontend/src/format.ts` (new), `frontend/src/components/PlaceCard.tsx`, `frontend/src/components/PriceStream.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/price.ts`, `frontend/src/components/CoverageMap.tsx`, `frontend/src/vite-env.d.ts`
- deleted: `frontend/src/components/ModeToggle.tsx`, `frontend/src/mocks/priceStream.ts`, `frontend/src/api/places.ts`, `frontend/public/mocks/places-etalon.json`, `frontend/public/mocks/places-backup.json`
- kept: `frontend/public/mocks/coverage.json`, unused `ApiMode` in `contract.ts`, unused Dockerfile `VITE_API_MODE_DEFAULT` ARG

## Not touched
- R1 tiles: style URL, no self-host, no "map unavailable" fallback.
- R2 AI input: `IngredientMenu.tsx` not edited; "Drugoe" stays disabled; no `POST /api/parse`.
- Frozen IA F1-F4: PlaceCards stay short; objects only in PlaceDetails; AlmostFits top-5 + show more; OriginForm+PriceStream in `.stage-price`; collapsed menu; App preselects top-1; default `ETALON_INGREDIENTS`; no density<=1 glow; client does not sort `places[]`.
- PlaceList/AlmostFits selection, share, grey cards, "Buy on Tutu" states.
- backend/**, schema.sql, plans/api-contract.md, `frontend/src/types/contract.ts`.
- `.env`, `BURGER_SC_PRICE_ACCEPTED`, no Docker rebuild, no push, no merge to main.
