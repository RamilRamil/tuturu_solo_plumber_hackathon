-- Burger SQLite schema (G1). Source of truth for A/B/C models.
-- Precedence: schema.sql > plans/api-contract.md > plans/00-orchestration.md §0 > mvp-spec.md
-- mvp-spec.md §5 hub.sellable_modes as a direction-independent node attribute is CANCELLED (B2).
-- mvp-spec.md §12 "cut pairs first" is CANCELLED (B4).
-- One model layer: lib/models.py (dataclasses). Do not add SQLAlchemy models.

-- ---------------------------------------------------------------------------
-- Identity (frozen here, format detailed in plans/api-contract.md / G2)
--   hub.id        = name + "|" + subject   (comma FORBIDDEN)
--   cluster.id    = "c:" + ",".join(sorted(hub.id))
--   cluster identity = set of hub.id. Radius is NOT part of identity.
--   Phase is NOT part of identity. Title is human text, not a key.
--   Same hub set at 50/100/150 km => same cluster.id
-- ---------------------------------------------------------------------------

-- G3 expected_region (general case, not the Rostov Veliky etalon):
--   Rostov Veliky EXISTS in cities_ru as name "Rostov" / subject Yaroslavl oblast.
--   If hub is IN cities_ru: expected_region = cities_ru.subject (canonical vs OSM).
--   If hub is NOT in the 1134-city handbook: expected_region = OSM admin_level=4
--     polygon name:ru (else name) via point-in-polygon.
--   If no admin_level=4 polygon: probe_status=misresolved, do NOT delete the hub.
--   If handbook subject and OSM admin_level=4 disagree: subject wins; OSM goes to
--     misresolve_log only (source='osm_subject_mismatch').
--   Full freeze: plans/g3-expected-region.md

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hub (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  subject TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  population INTEGER,
  tutu_geo_id TEXT,
  resolved_name TEXT,
  resolved_region TEXT,
  -- B1: three probe outcomes. misresolved MUST NOT be collapsed into not_sellable.
  probe_status TEXT NOT NULL CHECK (probe_status IN ('sellable', 'not_sellable', 'misresolved')),
  -- D1 snapshot of modes on the Moscow->hub probe. NOT direction-independent.
  -- Empty string means no paid mode on that probe (on-foot card), not "delete me".
  sellable_modes TEXT NOT NULL DEFAULT '',
  -- Derived from leg (recompute after D2). NOT a property of a direction.
  -- 1 iff EXISTS an ok leg that can reach this hub from a reference origin set.
  reachable_from_any INTEGER NOT NULL DEFAULT 0 CHECK (reachable_from_any IN (0, 1)),
  -- G3: where expected_region for guard came from
  expected_region TEXT,
  expected_region_source TEXT NOT NULL DEFAULT 'cities_ru.subject'
    CHECK (expected_region_source IN (
      'cities_ru.subject',
      'osm.admin_level_4',
      'missing'
    )),
  min_price_from_moscow INTEGER,
  latency_ms INTEGER,
  checked_at TEXT
);

CREATE TABLE IF NOT EXISTS poi (
  id TEXT PRIMARY KEY,
  osm_type TEXT NOT NULL CHECK (osm_type IN ('node', 'way', 'relation')),
  osm_id INTEGER NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  name TEXT,
  ingredient_id TEXT NOT NULL,
  wikidata TEXT,
  wikipedia TEXT,
  start_date_raw TEXT,
  start_date_from INTEGER,
  start_date_to INTEGER,
  opening_hours TEXT,
  hours_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (hours_status IN ('open', 'closed', 'unknown')),
  significance REAL NOT NULL DEFAULT 0,
  tags_json TEXT NOT NULL DEFAULT '{}',
  hub_id TEXT,
  FOREIGN KEY (hub_id) REFERENCES hub(id)
);

CREATE INDEX IF NOT EXISTS idx_poi_lat_lon ON poi(lat, lon);
CREATE INDEX IF NOT EXISTS idx_poi_ingredient ON poi(ingredient_id);

-- B2: sellability of a hop is a property of a directed edge, not of a hub.
CREATE TABLE IF NOT EXISTS leg (
  origin_hub TEXT NOT NULL,
  dest_hub TEXT NOT NULL,
  date_probed TEXT NOT NULL,
  modes TEXT NOT NULL DEFAULT '',
  min_price INTEGER,
  duration_min INTEGER,
  latency_ms INTEGER,
  checked_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('ok', 'no_route', 'misresolved')),
  PRIMARY KEY (origin_hub, dest_hub, date_probed),
  FOREIGN KEY (origin_hub) REFERENCES hub(id),
  FOREIGN KEY (dest_hub) REFERENCES hub(id)
);

CREATE INDEX IF NOT EXISTS idx_leg_origin_dest ON leg(origin_hub, dest_hub);

-- Precompute key is (id, radius_km). Public identity is id only (G2).
CREATE TABLE IF NOT EXISTS cluster (
  id TEXT NOT NULL,
  radius_km INTEGER NOT NULL,
  hub_ids TEXT NOT NULL,
  title TEXT,
  center_lat REAL,
  center_lon REAL,
  diameter_km REAL,
  ingredient_mask TEXT,
  PRIMARY KEY (id, radius_km)
);

CREATE TABLE IF NOT EXISTS route_cache (
  origin_hub TEXT NOT NULL,
  dest_hub TEXT NOT NULL,
  date TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (origin_hub, dest_hub, date)
);

CREATE TABLE IF NOT EXISTS hotel_cache (
  hub_id TEXT NOT NULL,
  check_in TEXT NOT NULL,
  check_out TEXT NOT NULL,
  adults INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (hub_id, check_in, check_out, adults)
);

CREATE TABLE IF NOT EXISTS misresolve_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  requested TEXT NOT NULL,
  got_name TEXT,
  got_region TEXT,
  expected_region TEXT,
  expected_region_source TEXT,
  at TEXT NOT NULL
);

-- Raw MCP tool responses. lib/tutu_mcp.py writes HERE before any guard/business processing.
CREATE TABLE IF NOT EXISTS mcp_cache (
  tool TEXT NOT NULL,
  args_hash TEXT NOT NULL,
  args_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (tool, args_hash)
);
