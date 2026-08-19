# Stream D report - named POI display

Worktree: `.worktrees/named-poi`
Branch: `codex/frontend-named-poi`
Not merged, not pushed.

## What shipped

- PlaceCard lists only POIs with a non-empty name after trim. `null` / `undefined` / `""` / whitespace do not render as blank rows.
- ClusterMap features and popups use the same named subset. Hubs are unchanged.
- Count line is `{named} of {total} named` on the card and on the map. The number is total objects (named + unnamed). Visible list/markers are the named subset.
- Coverage chips, rarity, hub chips, grey-card / on-foot rules and copy, etalon `cluster_id`, `ALMOST_FITS_PAIR_ID`, ingredients, ranking: not touched.
- Unnamed POIs stay in `place.objects[]`. This is a display filter only. Coverage math stays on the backend.

## Build

```
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
cd frontend && npm ci && npm run build
```

**PASS** (`tsc --noEmit && vite build`). MapLibre chunk-size warning only. `npm ci` was required: this worktree had no `node_modules`.

## Remaining

- Live OSM dump was not clicked in a browser here; the guard is runtime on `obj.name`.
- Unnamed POIs still arrive in the API payload; this stream does not drop them from coverage.
