"""Dataclass models matching schema.sql. The only model layer (no SQLAlchemy)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"

CLUSTER_ID_PREFIX = "c:"
HUB_ID_SEP = "|"

ProbeStatus = Literal["sellable", "not_sellable", "misresolved"]
LegStatus = Literal["ok", "no_route", "misresolved"]
HoursStatus = Literal["open", "closed", "unknown"]
RegionSource = Literal["cities_ru.subject", "osm.admin_level_4", "missing"]


def make_hub_id(name: str, subject: str) -> str:
    """Stable hub id: name|subject. Comma is forbidden (cluster_id joins on comma)."""
    hid = name.strip() + HUB_ID_SEP + subject.strip()
    if "," in hid:
        raise ValueError("hub_id must not contain comma")
    if hid.count(HUB_ID_SEP) != 1:
        raise ValueError("hub_id must contain exactly one pipe separator")
    return hid


def make_cluster_id(hub_ids: list[str]) -> str:
    """Identity = set of hub.id. Radius and phase are not part of the id."""
    if not hub_ids:
        raise ValueError("cluster_id requires at least one hub_id")
    for hid in hub_ids:
        if "," in hid:
            raise ValueError("hub_id must not contain comma")
        if not hid:
            raise ValueError("empty hub_id")
    return CLUSTER_ID_PREFIX + ",".join(sorted(set(hub_ids)))


def pax_sig(children_ages: list[int] | tuple[int, ...] | None) -> str:
    """Stable passenger signature. Empty string means no children."""
    ages = sorted(int(a) for a in (children_ages or []) if int(a) > 0)
    return ",".join(str(a) for a in ages)


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(%s)" % table)}


def migrate_cache_identity(conn: sqlite3.Connection) -> None:
    """Widen route_cache / hotel_cache PK with adults + pax_sig. Safe on new DBs."""
    route_cols = _table_cols(conn, "route_cache")
    if route_cols and "pax_sig" not in route_cols:
        conn.executescript(
            """
            CREATE TABLE route_cache_v2 (
              origin_hub TEXT NOT NULL,
              dest_hub TEXT NOT NULL,
              date TEXT NOT NULL,
              adults INTEGER NOT NULL DEFAULT 1,
              pax_sig TEXT NOT NULL DEFAULT '',
              payload_json TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              PRIMARY KEY (origin_hub, dest_hub, date, adults, pax_sig)
            );
            INSERT INTO route_cache_v2(
              origin_hub, dest_hub, date, adults, pax_sig, payload_json, fetched_at
            )
            SELECT origin_hub, dest_hub, date, 1, '', payload_json, fetched_at
            FROM route_cache;
            DROP TABLE route_cache;
            ALTER TABLE route_cache_v2 RENAME TO route_cache;
            """
        )
    hotel_cols = _table_cols(conn, "hotel_cache")
    if hotel_cols and "pax_sig" not in hotel_cols:
        conn.executescript(
            """
            CREATE TABLE hotel_cache_v2 (
              hub_id TEXT NOT NULL,
              check_in TEXT NOT NULL,
              check_out TEXT NOT NULL,
              adults INTEGER NOT NULL,
              pax_sig TEXT NOT NULL DEFAULT '',
              payload_json TEXT NOT NULL,
              fetched_at TEXT NOT NULL,
              PRIMARY KEY (hub_id, check_in, check_out, adults, pax_sig)
            );
            INSERT INTO hotel_cache_v2(
              hub_id, check_in, check_out, adults, pax_sig, payload_json, fetched_at
            )
            SELECT hub_id, check_in, check_out, adults, '', payload_json, fetched_at
            FROM hotel_cache;
            DROP TABLE hotel_cache;
            ALTER TABLE hotel_cache_v2 RENAME TO hotel_cache;
            """
        )


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    migrate_cache_identity(conn)
    conn.commit()


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_schema(conn)
    return conn


@dataclass
class Hub:
    id: str
    name: str
    subject: str
    lat: float
    lon: float
    probe_status: ProbeStatus
    population: Optional[int] = None
    tutu_geo_id: Optional[str] = None
    resolved_name: Optional[str] = None
    resolved_region: Optional[str] = None
    sellable_modes: str = ""
    reachable_from_any: int = 0
    expected_region: Optional[str] = None
    expected_region_source: RegionSource = "cities_ru.subject"
    min_price_from_moscow: Optional[int] = None
    latency_ms: Optional[int] = None
    checked_at: Optional[str] = None


@dataclass
class Poi:
    id: str
    osm_type: str
    osm_id: int
    lat: float
    lon: float
    ingredient_id: str
    name: Optional[str] = None
    wikidata: Optional[str] = None
    wikipedia: Optional[str] = None
    start_date_raw: Optional[str] = None
    start_date_from: Optional[int] = None
    start_date_to: Optional[int] = None
    opening_hours: Optional[str] = None
    hours_status: HoursStatus = "unknown"
    significance: float = 0.0
    tags_json: str = "{}"
    hub_id: Optional[str] = None


@dataclass
class Leg:
    origin_hub: str
    dest_hub: str
    date_probed: str
    status: LegStatus
    modes: str = ""
    min_price: Optional[int] = None
    duration_min: Optional[int] = None
    latency_ms: Optional[int] = None
    checked_at: Optional[str] = None


@dataclass
class Cluster:
    id: str
    radius_km: int
    hub_ids: str
    title: Optional[str] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    diameter_km: Optional[float] = None
    ingredient_mask: Optional[str] = None
