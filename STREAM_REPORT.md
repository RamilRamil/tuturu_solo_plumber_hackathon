# STREAM_REPORT — Worker D (frontend-ia)

Branch: `codex/frontend-ia`
Worktree: `.worktrees/frontend-ia`
Scope: `frontend/**` only (+ this report)
Build: `npm run build` (Node v20.20.2) — pass
SC-D2: client does not sort `places[]` / almost-fits; only `slice(0, 5)` in API order. Remaining `.sort()` is ingredient-set compare in `api/places.ts` (untouched).

## F1 — short list

- `PlaceCard` no longer renders `<ul className="objects">`. Card = title, hub chips + `diameter_km`, coverage matched/missing, `rarity.rank/total_places_with_combo`, on-foot / grey reason. Probe badges and grey routing copy unchanged.
- Named-POI helper (`N of M named` + named list) moved to new `PlaceDetails.tsx` for `selectedPlace` only.
- Hours: `HoursStatus` returns null unless open/closed. Map popup no longer prints unknown / "неизвестно".
- `PlaceList` still shows top-5; the rest is behind "Показать ещё" (API order).
- `AlmostFits` same: first 5, rest collapsed. Unselected clusters never render objects.

## F2 — price and buy

- After a place is selected, `OriginForm` + `PriceStream` sit in `.stage-price` next to map/details (3-column `.stage.has-selection`), not the page footer. Origin still only after selection.
- `PriceStream` summary: large `breakdown.total`, legs (`from→to`, fare/mode, "нет тарифа" if `price===0`), hotels stay_total, `price_status`. Raw SSE log under `<details>подробности</details>`.
- Buy CTA: large "Купить на Tutu" from `checkout.data.items[].checkout_url`. Streaming without checkout: "считаем маршрут…". Done/blocking warnings without ticket: "до этого места билета нет". Live Tutu fares not fixed here (surface only).

## F3 — entry and map

- `IngredientMenu`: if `selected.length > 0`, starts collapsed (chip row + "Изменить"). Full palette only in edit mode.
- Places load: keep share `cluster_id` if present in the response; else first FULL coverage place; else `places[0]`. No sort. Avoids empty MapLibre.
- Cards: explicit hover/selected + `cursor: pointer`.

## F4 — honest default

- Default ingredients remain `ETALON_INGREDIENTS` (`ancient_temple` + `industrial_museum`). Share URL combo is not rewritten.
- `density_measured <= 1` is not shown as a count badge (no ultra-rare glow).

## Do-not

- Did not edit `types/contract.ts` or `api/*.ts`.
- Did not change grey-card / on-foot logic.
- Did not push or merge.

## Files

- `frontend/src/components/PlaceDetails.tsx` (new)
- `frontend/src/components/PlaceCard.tsx`
- `frontend/src/components/PlaceList.tsx`
- `frontend/src/components/AlmostFits.tsx`
- `frontend/src/components/HoursStatus.tsx`
- `frontend/src/components/ClusterMap.tsx`
- `frontend/src/components/PriceStream.tsx`
- `frontend/src/components/IngredientMenu.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
