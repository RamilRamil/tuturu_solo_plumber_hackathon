"""Build place cards from hub discs and POI. Exact ingredient_id match. Live discs."""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from lib.models import make_cluster_id

from backend.services.cluster_candidates import iter_candidates
from backend.services.cluster_config import DEFAULT_LIMIT, R_LOCAL_KM
from backend.services.cluster_geo import haversine_km
from backend.services.cluster_rank import rank_places

TITLE_JOIN = " and "


def burger_db_path() -> str:
    return os.environ.get("BURGER_DB", "data/burger.db")


def open_db(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or burger_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_hubs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, name, subject, lat, lon, probe_status, population FROM hub"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "subject": r["subject"],
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "probe_status": r["probe_status"],
            "population": r["population"] if r["population"] is not None else 0,
        }
        for r in rows
    ]


def load_pois(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, name, lat, lon, ingredient_id, wikidata, wikipedia,
               start_date_raw, start_date_from, start_date_to,
               opening_hours, hours_status, significance, tags_json, hub_id
        FROM poi
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "ingredient_id": r["ingredient_id"],
                "wikidata": r["wikidata"],
                "wikipedia": r["wikipedia"],
                "start_date_raw": r["start_date_raw"],
                "start_date_from": r["start_date_from"],
                "start_date_to": r["start_date_to"],
                "opening_hours": r["opening_hours"],
                "hours_status": r["hours_status"],
                "significance": compute_significance(r),
                "tags_json": r["tags_json"],
                "hub_id": r["hub_id"],
            }
        )
    return out


def compute_significance(row: sqlite3.Row | dict[str, Any]) -> float:
    has_wikidata = 1.0 if row["wikidata"] else 0.0
    has_wikipedia = 1.0 if row["wikipedia"] else 0.0
    has_start = (
        1.0
        if (row["start_date_raw"] or row["start_date_from"] is not None or row["start_date_to"] is not None)
        else 0.0
    )
    has_name = 1.0 if row["name"] else 0.0
    raw_tags = row["tags_json"] or "{}"
    if isinstance(raw_tags, dict):
        tags = raw_tags
    else:
        try:
            tags = json.loads(raw_tags)
        except (TypeError, ValueError):
            tags = {}
    ntags = len(tags) if isinstance(tags, dict) else 0
    return (
        3.0 * has_wikidata
        + 2.0 * has_wikipedia
        + 2.0 * has_start
        + 1.0 * has_name
        + min(ntags / 5.0, 2.0)
    )


def poi_in_discs(poi: dict[str, Any], hubs: tuple[dict[str, Any], ...], r_local_km: float) -> bool:
    for hub in hubs:
        if haversine_km(poi["lat"], poi["lon"], hub["lat"], hub["lon"]) <= r_local_km:
            return True
    return False


def _start_date(poi: dict[str, Any]) -> dict[str, Any] | None:
    if (
        poi["start_date_raw"] is None
        and poi["start_date_from"] is None
        and poi["start_date_to"] is None
    ):
        return None
    return {
        "raw": poi["start_date_raw"],
        "from": poi["start_date_from"],
        "to": poi["start_date_to"],
    }


def _diameter_km(pois: list[dict[str, Any]]) -> float:
    if len(pois) < 2:
        return 0.0
    best = 0.0
    for i in range(len(pois)):
        for j in range(i + 1, len(pois)):
            d = haversine_km(pois[i]["lat"], pois[i]["lon"], pois[j]["lat"], pois[j]["lon"])
            if d > best:
                best = d
    return best


def build_place(
    hubs: tuple[dict[str, Any], ...],
    all_pois: list[dict[str, Any]],
    ingredients: list[str],
    radius_km: int,
    r_local_km: float = R_LOCAL_KM,
) -> dict[str, Any] | None:
    burger = set(ingredients)
    matched_pois = [
        p
        for p in all_pois
        if p["ingredient_id"] in burger and poi_in_discs(p, hubs, r_local_km)
    ]
    if not matched_pois:
        return None
    hub_ids = [h["id"] for h in hubs]
    covered = {p["ingredient_id"] for p in matched_pois}
    matched = [i for i in ingredients if i in covered]
    missing = [i for i in ingredients if i not in covered]
    ordered_hubs = sorted(hubs, key=lambda h: h["id"])
    title = TITLE_JOIN.join(h["name"] for h in ordered_hubs)
    center_lat = sum(h["lat"] for h in hubs) / len(hubs)
    center_lon = sum(h["lon"] for h in hubs) / len(hubs)
    pop = sum(int(h["population"] or 0) for h in hubs)
    on_foot = 0 if all(h["probe_status"] == "sellable" for h in hubs) else 1
    objects = [
        {
            "id": p["id"],
            "name": p["name"],
            "ingredient": p["ingredient_id"],
            "lat": p["lat"],
            "lon": p["lon"],
            "significance": p["significance"],
            "wikidata": p["wikidata"],
            "start_date": _start_date(p),
            "opening_hours": p["opening_hours"],
            "hours_status": p["hours_status"],
        }
        for p in matched_pois
    ]
    return {
        "cluster_id": make_cluster_id(hub_ids),
        "title": title,
        "hubs": [
            {
                "hub_id": h["id"],
                "name": h["name"],
                "region": h["subject"],
                "lat": h["lat"],
                "lon": h["lon"],
                "probe_status": h["probe_status"],
            }
            for h in ordered_hubs
        ],
        "center": {"lat": center_lat, "lon": center_lon},
        "diameter_km": _diameter_km(matched_pois),
        "coverage": {"matched": matched, "missing": missing},
        "objects": objects,
        "sum_significance": sum(p["significance"] for p in matched_pois),
        "population": pop,
        "on_foot": on_foot,
        "radius_km": radius_km,
    }


def persist_clusters(
    conn: sqlite3.Connection,
    places: list[dict[str, Any]],
    radius_km: int,
) -> None:
    """Write live discs so POST /api/price can load the clicked cluster_id."""
    sql = (
        "INSERT OR REPLACE INTO cluster("
        "id, radius_km, hub_ids, title, center_lat, center_lon, diameter_km, ingredient_mask"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for place in places:
        hub_ids = [h["hub_id"] for h in place["hubs"]]
        conn.execute(
            sql,
            (
                place["cluster_id"],
                int(radius_km),
                json.dumps(hub_ids, ensure_ascii=False),
                place.get("title") or "",
                float(place["center"]["lat"]),
                float(place["center"]["lon"]),
                float(place.get("diameter_km") or 0.0),
                json.dumps(place.get("coverage") or {}, ensure_ascii=True),
            ),
        )
    conn.commit()


def list_places(
    conn: sqlite3.Connection,
    ingredients: list[str],
    radius_km: int,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    hubs = load_hubs(conn)
    pois = load_pois(conn)
    raw: list[dict[str, Any]] = []
    for hub_set in iter_candidates(hubs, float(radius_km)):
        place = build_place(hub_set, pois, ingredients, radius_km)
        if place is not None:
            raw.append(place)
    ranked = rank_places(raw, ingredients, radius_km)
    persist_clusters(conn, ranked, radius_km)
    cap = max(0, int(limit))
    return {"total_found": len(ranked), "places": ranked[:cap]}
