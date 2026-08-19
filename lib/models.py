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


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
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
