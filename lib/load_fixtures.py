"""Load golden fixtures/ into a SQLite DB in schema.sql shape."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from lib.models import apply_schema
from lib.tutu_mcp import args_hash

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"

HUB_COLS = (
    "id", "name", "subject", "lat", "lon", "population", "tutu_geo_id",
    "resolved_name", "resolved_region", "probe_status", "sellable_modes",
    "reachable_from_any", "expected_region", "expected_region_source",
    "min_price_from_moscow", "latency_ms", "checked_at",
)
POI_COLS = (
    "id", "osm_type", "osm_id", "lat", "lon", "name", "ingredient_id",
    "wikidata", "wikipedia", "start_date_raw", "start_date_from", "start_date_to",
    "opening_hours", "hours_status", "significance", "tags_json", "hub_id",
)
LEG_COLS = (
    "origin_hub", "dest_hub", "date_probed", "modes", "min_price",
    "duration_min", "latency_ms", "checked_at", "status",
)
CLUSTER_COLS = (
    "id", "radius_km", "hub_ids", "title", "center_lat", "center_lon",
    "diameter_km", "ingredient_mask",
)
HOTEL_COLS = ("hub_id", "check_in", "check_out", "adults", "pax_sig", "payload_json", "fetched_at")
MIS_COLS = (
    "requested", "got_name", "got_region", "expected_region",
    "expected_region_source", "at",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _insert(conn: sqlite3.Connection, table: str, cols: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    placeholders = ",".join("?" for _ in cols)
    col_sql = ",".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({placeholders})"
    for row in rows:
        conn.execute(sql, tuple(row.get(c) for c in cols))


def load_golden_fixtures(conn: sqlite3.Connection, root: Path = FIXTURES_ROOT) -> None:
    apply_schema(conn)
    rows_dir = root / "rows"
    _insert(conn, "hub", HUB_COLS, _read_json(rows_dir / "hubs.json"))
    _insert(conn, "poi", POI_COLS, _read_json(rows_dir / "poi.json"))
    _insert(conn, "leg", LEG_COLS, _read_json(rows_dir / "legs.json"))
    _insert(conn, "cluster", CLUSTER_COLS, _read_json(rows_dir / "clusters.json"))
    hotels = _read_json(rows_dir / "hotel_cache.json")
    for h in hotels:
        h["payload_json"] = _as_json_text(h["payload_json"])
        h.setdefault("pax_sig", "")
    _insert(conn, "hotel_cache", HOTEL_COLS, hotels)
    _insert(conn, "misresolve_log", MIS_COLS, _read_json(rows_dir / "misresolve_log.json"))
    _load_mcp_cache(conn, root, _read_json(rows_dir / "mcp_cache.json"))
    conn.commit()


def _load_mcp_cache(conn: sqlite3.Connection, root: Path, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        args = entry.get("args_json") or {}
        if isinstance(args, str):
            args = json.loads(args)
        payload: Any
        rel = entry.get("payload_file")
        if rel:
            wrapped = _read_json(root / rel)
            if isinstance(wrapped, dict) and "mcp" in wrapped:
                payload = wrapped["mcp"]
            else:
                payload = wrapped.get("payload", wrapped)
        else:
            payload = entry.get("payload_json")
            if isinstance(payload, str):
                payload = json.loads(payload)
        tool = entry["tool"]
        digest = entry.get("args_hash") or args_hash(tool, args)
        conn.execute(
            """
            INSERT OR REPLACE INTO mcp_cache(tool, args_hash, args_json, payload_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tool,
                digest,
                json.dumps(args, ensure_ascii=True),
                json.dumps(payload, ensure_ascii=True),
                entry.get("fetched_at") or "2026-08-19T00:00:00Z",
            ),
        )
