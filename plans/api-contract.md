# API contract (G2)

Frozen seam for streams B, C, D. Changes go through the Architect.

Precedence: `schema.sql` > this file > `plans/00-orchestration.md` §0 > `mvp-spec.md`.
`mvp-spec.md` §5 (`sellable_modes` as a node attribute) and §12 (cut pairs first) are cancelled.

Backend: one FastAPI process, port 8000 (see `plans/stack.md`). This file is the contract only; product handlers are owned by B and C after basket A is green.

---

## cluster_id (frozen)

Identity of a cluster is the **set of `hub.id`**. Radius is not in the id. Phase is not in the id. `title` is human text, not a key.

```
cluster_id = "c:" + ",".join(sorted(hub_id))
hub.id     = name + "|" + subject     # comma forbidden
```

Helpers: `lib.models.make_hub_id`, `lib.models.make_cluster_id`.
`make_hub_id` **rejects comma** in name or subject (cluster_id joins on comma).
Cyrillic and `|` in the id are allowed. Share URLs (FR-D16) must
**percent-encode** the whole `cluster_id` (UTF-8); do not treat the raw string
as a path segment.

Invariants:

- The same hub set at 50 / 100 / 150 km **must** produce the same `cluster_id`.
- Precompute rows live in `cluster(id, radius_km, ...)` with PK `(id, radius_km)`. Public id is `id` only.
- `POST /api/price` accepts this id. Unknown id → **404**.
- `load_cluster_row` reads table `cluster` only. Missing row → **404**. Do not rebuild the cluster from `hub.id` existence.
- Sharing a result uses this id; a radius change that does not change the hub set does not mint a new id.

Example (etalon #1, two hubs):

```
c:Ростов|Ярославская область,Ярославль|Ярославская область
```

Title (not a key): `Yaroslavl and Rostov Veliky` / human Russian in UI.

Backup single-hub burger (B4), Yaroslavl only:

```
c:Ярославль|Ярославская область
```

---

## POST /api/places  (phase 1, Worker B, < 200 ms, no network)

Request:

```json
{
  "ingredients": ["ancient_temple", "industrial_museum"],
  "radius_km": 100,
  "limit": 20
}
```

| field | rules |
|---|---|
| `ingredients` | non-empty list of `ingredients.yaml` ids |
| `radius_km` | discrete: `50` \| `100` \| `150` only. Default 100. Above 150 → 400 (D2 cap). |
| `limit` | default 20 |

Response (sync):

```json
{
  "total_found": 12,
  "places": [ { "...Place..." } ]
}
```

### Place object

```json
{
  "cluster_id": "c:Ростов|Ярославская область,Ярославль|Ярославская область",
  "title": "Yaroslavl and Rostov Veliky",
  "hubs": [
    {
      "hub_id": "Ярославль|Ярославская область",
      "name": "Yaroslavl",
      "region": "Yaroslavl oblast",
      "lat": 57.61667,
      "lon": 39.85,
      "probe_status": "sellable"
    }
  ],
  "center": { "lat": 57.4, "lon": 39.6 },
  "diameter_km": 58,
  "coverage": {
    "matched": ["ancient_temple", "industrial_museum"],
    "missing": []
  },
  "rarity": { "rank": 3, "total_places_with_combo": 7 },
  "objects": [
    {
      "id": "n123",
      "name": "Church of the Resurrection",
      "ingredient": "ancient_temple",
      "lat": 57.18,
      "lon": 39.41,
      "significance": 7,
      "wikidata": "Q123",
      "start_date": { "raw": "1670", "from": 1670, "to": 1670 },
      "opening_hours": null,
      "hours_status": "unknown"
    }
  ]
}
```

JSON in live responses may use Russian `name`/`title`/`region` copied from DB. Field names stay ASCII.

### Sorting of `places[]` (B3, frozen)

Lexicographic, not a weighted sum alone:

1. **covered ingredient count** descending (`len(coverage.matched)`).
2. **`cluster_score` descending** (formula in `plans/worker-B-phase1.md`; weights in config).

A cluster that covers both burger ingredients always ranks above a cluster that covers one, regardless of density. `coverage_ratio` dominates via this lexicographic key, not via a large weight.

`rarity.rank` is 1-based among clusters that share the same matched-ingredient set; `total_places_with_combo` is that set's size. `rarity` in the score is `1 / total_places_with_combo`.

### Hub flags in phase 1 (B2)

Do **not** send `sellable: true` as if tickets existed in every direction.

- `hubs[].probe_status` ∈ `{sellable, not_sellable, misresolved}` from table `hub`.
- `not_sellable` → UI mark "on your own" (card stays).
- Ticketability of a hop after origin is table `leg`, phase 2. Unreachable cards grey out with a reason; they do not vanish.

---

## POST /api/price  (phase 2, Worker C, SSE)

Request:

```json
{
  "cluster_id": "c:Ростов|Ярославская область,Ярославль|Ярославская область",
  "origin": "Moscow",
  "days": 3,
  "month": "2026-10",
  "adults": 1,
  "children_ages": [],
  "budget_scope": "transport"
}
```

| field | rules |
|---|---|
| `cluster_id` | exact G2 id. Unknown → **404** (not an SSE `warning`). |
| `origin` | city name; Worker C resolves via `lib/tutu_mcp.py` + guard. |
| `days` | integer ≥ 1 |
| `month` | `YYYY-MM` |
| `adults` | integer ≥ 1 |
| `children_ages` | list of integers (years). Default `[]`. |
| `budget_scope` | `"transport"` \| `"all"`. Default `"transport"`. |

Response: `Content-Type: text/event-stream`. Nginx must not buffer (see `nginx/nginx.conf`, G6). Each event:

```
event: <name>
data: <json>

```

Event names (payload of `data:`): `resolved` | `leg` | `hotel` | `breakdown` | `checkout` | `warning` | `done`.

SSE events stay sequential (one event then the next). Blocking MCP/SQLite work runs off the FastAPI event loop. Artificial 3s/1s pauses are opt-in via `BURGER_PRICE_DEMO_PACE=1`. Default live path has no extra sleep on top of MCP latency. Date windows are lazy (V3).

Route cache lookup key is `(origin_hub, dest_hub, requested day, adults, pax_sig)`. Do not substitute `leg.date_probed` as the cache date. Exact miss: live Tutu if `BURGER_LIVE_TUTU`, else last-resort `leg` row with warning `stale_leg` (not mixed with `misresolved` / `not_sellable` / `no_route`). Checkout URL and price share the same date and pax. `search_multitransport` is adults-only: non-empty `children_ages` emits `child_fare_unverified` and still queries adults. `search_hotels` accepts `children_ages`.

### `resolved`

```json
{
  "origin": {
    "query": "Moscow",
    "name": "Moscow",
    "region": "Moscow",
    "geo_id": null,
    "guard": "ok"
  },
  "hubs": [
    {
      "hub_id": "Ярославль|Ярославская область",
      "query": "Yaroslavl",
      "name": "Yaroslavl",
      "region": "Yaroslavl oblast",
      "guard": "ok"
    }
  ]
}
```

`guard` ∈ `{ok, misresolved}`. Guard runs in `lib/tutu_mcp.py` before any price is shown. `misresolved` does not become `not_sellable`.

### `leg`

```json
{
  "from_hub": "Москва|Москва",
  "to_hub": "Ярославль|Ярославская область",
  "from_name": "Moscow",
  "to_name": "Yaroslavl",
  "mode": "railway",
  "modes": "avia,railway,bus",
  "price": 1035,
  "currency": "RUB",
  "duration_min": null,
  "date": "2026-10-09",
  "checkout_ref": {},
  "source": "live"
}
```

`source` ∈ `{live, cache}`. Optional `stale: true` when the hop used a last-resort `leg` row instead of exact `route_cache` for the requested day. Price `0` is absence (drop the mode; do not show 0 RUB as a fare). `checkout_ref` is an opaque object from Tutu; pass through. Checkout URL and `price`/`date` must come from the same cache or live payload.

If the directed `leg` row is `no_route` or missing, do not invent a composite. Emit `warning` and keep the card (grey).

### `hotel`

```json
{
  "hub_id": "Ярославль|Ярославская область",
  "city": "Yaroslavl",
  "min_price": 750,
  "currency": "RUB",
  "nights": 1,
  "price_basis": "stay_total",
  "checkout_ref": {},
  "source": "live"
}
```

`min_price` is `stay_total` for the whole stay. Do not multiply by `nights`.

### `breakdown` (required before `done` if any price was shown)

```json
{
  "transport": 2592,
  "lodging": 1750,
  "total": 4342,
  "currency": "RUB",
  "budget_scope": "all",
  "price_status": "fixture-confirmed"
}
```

`price_status` ∈ `{fixture-confirmed, live}`. Overall `breakdown`/`done` status stays `fixture-confirmed` unless env `BURGER_SC_PRICE_ACCEPTED` is truthy. That env is the **only** way overall status may become `live`. One live hop (`source: live`) must not flip overall status. Do not treat fixture totals as SC-price. Per-item `source` stays `live|cache`.

### `checkout`

```json
{
  "items": [
    {
      "kind": "leg",
      "from_hub": "Москва|Москва",
      "to_hub": "Ярославль|Ярославская область",
      "checkout_url": "https://www.tutu.ru/example"
    }
  ]
}
```

Reproduce `checkout_url` exactly as returned. Do not rebuild or trim.

### `warning`

```json
{
  "code": "misresolved",
  "message": "guard rejected destination",
  "hub_id": null,
  "leg": { "from_hub": "", "to_hub": "" },
  "recovered": true
}
```

`code` examples (keep distinct): `misresolved`, `not_sellable`, `no_route`, `no_price`, `no_hotel`, `hours_unknown`, `cache_fallback`, `stale_leg`, `child_fare_unverified`.

Optional `recovered: true` on `no_route` when the return hop failed and fallback from the previous city succeeded. The UI must not grey the whole cluster in that case. Omit `recovered` when false.

### `done`

```json
{
  "ok": true,
  "cluster_id": "c:Ростов|Ярославская область,Ярославль|Ярославская область",
  "price_status": "fixture-confirmed"
}
```

---

## Errors (non-SSE)

| case | HTTP |
|---|---|
| unknown `cluster_id` on `/api/price` | 404 |
| invalid `radius_km` | 400 |
| empty `ingredients` | 400 |

---

## G3 pointer

Region source for guard: `plans/g3-expected-region.md`. Rostov Veliky is in `cities_ru` as `Rostov` / Yaroslavl oblast; the general case is an OSM node **outside** the 1134-city handbook.
