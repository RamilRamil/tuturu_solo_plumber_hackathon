# STREAM_REPORT (Worker D, R6-R7)

Branch: `codex/frontend-r67`
Worktree: `.worktrees/frontend-r67`
Base: main `7854c30` (R3-R5 already in tree)

## What changed

### R6 PriceStream details (P1)

- `<details>подробности</details>` no longer dumps raw SSE `warning` codes (`no_route`, `stale_leg`, ...).
- Shared labels in `frontend/src/format.ts` (`routingLabel` / `humanizeWarning`) so PlaceCard grey copy and the log match:
  - `no_route` -> «нет прямого рейса на плечо»
  - `stale_leg` -> «взят обходной вариант»
  - `not_sellable` -> «дальше своим ходом»
  - `misresolved` -> «город определён неверно»
  - `missing_price` / `no_price` -> «цены на плечо нет»
  - `cache_fallback` -> «live недоступен, показан cache» (longer ASCII `message` from backend is shown as-is)
  - `child_fare_unverified` -> short honest line about unverified child fare
- Consecutive identical user-facing warnings (same code + from/to, or same text) collapse to one row with `xN`.
- Hidden: `warning.recovered === true`; unrecovered-looking `no_route` / `stale_leg` that `noRouteRecovered` treats as internal hops. A `stale_leg` that is the shown priced pair stays (honest detour).
- Kept: `resolved` origin, priced `leg`/`hotel` via formatLeg/formatHotel, `breakdown` totals, `done`.
- Grey-card rules in App unchanged (`cache_fallback` still never greys). `noRouteRecovered` moved to `format.ts` only to share the filter.

### R7 Remove industrial_site (P1)

- Deleted `industrial_site` / «Действующие заводы» / `man_made=works` from `ingredients.yaml`.
- Removed from `INGREDIENTS` and `INGREDIENT_NAME_RU` in `frontend/src/catalog/ingredients.ts`.
- `industrial_museum` («Музеи техники») kept; density 1 still has no count badge (F4).
- `parsing_rules.name` no longer mentions the removed id.
- Old share URLs with `industrial_site` -> 400 unknown ingredient (no shim).
- Ingest `man_made=works` mapping left as-is. Specs/plans historical mentions left as-is.

## Not touched

- R1 tiles, R2 «Другое», R3 camera, R4 formatMoney, R5 live-only.
- `plans/api-contract.md`, `frontend/src/types/contract.ts`, backend/services/price.py, `.env`.
- No npm install, no push, no merge.

## Verify

- Frontend details list maps warnings; no raw `item.data.message` dump of codes.
- Catalog + yaml: no `industrial_site` ingredient id; `industrial_museum` present in both.
- IngredientMenu lists museum, not factories.
