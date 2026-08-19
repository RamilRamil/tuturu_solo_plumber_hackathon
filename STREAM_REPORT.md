# Stream report — frontend hardening

Worktree: `.worktrees/harden-frontend`  
Branch: `codex/harden-frontend`  
Not merged, not pushed.

## G. Coverage from live API

- Live mode fetches `/api/coverage` first. Static `/coverage.json` and `/mocks/coverage.json` are mock-only, or an explicit fallback when the live endpoint fails.
- No substring match between English and Russian labels. Matching is `regions[].slug` / `regions[].label` exact, or exact `regions_loaded` / `loaded` vs `admin_level_4`.
- If `regions[]` is present, the panel renders loaded / failed / not-in-snapshot from that list. Holes are regions marked not loaded, not a translated second copy of a loaded name.
- Current backend JSON still has English `regions_loaded` (e.g. `Yaroslavl oblast`). Those labels are shown as-is. Russian `admin_level_4` is not used as holes unless an exact label overlap exists.

## H. Frontend state

- `selectedId` starts null. Share `cluster_id` is restored only after `places[]` contains that id. Ingredients and radius from the share stay.
- After ingredients / radius / API mode change, `selectedId` is cleared immediately so OriginForm cannot stay on a stale cluster. It is restored only if the wanted id is in the new `places[]`.
- OriginForm `enabled={selectedPlace != null}` (the place object, not a dangling id string).
- Customer UI no longer shows the SC-D2 / G10 hint about the pair sitting below fifth.
- Grey cards: intermediate `warning.no_route` does not grey the card when `recovered: true` or a later priced return leg exists. `cache_fallback` remains a source badge, never a grey reason. `misresolved`, `not_sellable`, `no_route`, and `missing_price`/`no_price` stay separate.

## Build

```
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
cd frontend && npm run build
```

**PASS** (`tsc --noEmit && vite build`). MapLibre chunk-size warning only.

## Remaining

- Coverage panel is a list + legend, not a choropleth of Russia.
- Live `/api/coverage` against compose is wired; this stream did not exercise a running backend.
