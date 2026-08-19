"""Build place cards from hub discs and POI. Exact ingredient_id match. Live discs."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from typing import Any

from lib.models import make_cluster_id

from backend.services.cluster_candidates import iter_candidates
from backend.services.cluster_config import DEFAULT_LIMIT, R_LOCAL_KM
from backend.services.cluster_geo import haversine_km
from backend.services.cluster_rank import rank_places

TITLE_JOIN = " and "
PAIRWISE_DIAMETER_MAX_N = 40
_CENTER_EPS = 1e-9


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


def index_pois_by_hub(pois: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group POIs by ingest hub_id. Unattached rows are omitted."""
    indexed: dict[str, list[dict[str, Any]]] = {}
    for poi in pois:
        hid = poi.get("hub_id")
        if not hid:
            continue
        bucket = indexed.get(hid)
        if bucket is None:
            indexed[hid] = [poi]
        else:
            bucket.append(poi)
    return indexed


def pois_for_hubs(
    indexed: dict[str, list[dict[str, Any]]],
    hubs: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    """POIs attached to candidate hubs only. Attach radius 50km > r_local 25km."""
    if len(hubs) == 1:
        return list(indexed.get(hubs[0]["id"], ()))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hub in hubs:
        for poi in indexed.get(hub["id"], ()):
            pid = poi["id"]
            if pid in seen:
                continue
            seen.add(pid)
            out.append(poi)
    return out


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


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_hull_pois(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Andrew monotone chain on local km projection. Hull vertices keep full POI dicts."""
    n = len(pois)
    if n <= 2:
        return list(pois)
    lat0 = sum(p["lat"] for p in pois) / n
    cos0 = math.cos(math.radians(lat0))
    pts: list[tuple[float, float, dict[str, Any]]] = []
    for poi in pois:
        x = poi["lon"] * cos0
        y = poi["lat"]
        pts.append((x, y, poi))
    pts.sort(key=lambda t: (t[0], t[1], t[2]["id"]))

    def _push(hull: list[tuple[float, float, dict[str, Any]]], item: tuple[float, float, dict[str, Any]]) -> None:
        while len(hull) >= 2 and _cross((hull[-2][0], hull[-2][1]), (hull[-1][0], hull[-1][1]), (item[0], item[1])) <= 0:
            hull.pop()
        hull.append(item)

    lower: list[tuple[float, float, dict[str, Any]]] = []
    for item in pts:
        _push(lower, item)
    upper: list[tuple[float, float, dict[str, Any]]] = []
    for item in reversed(pts):
        _push(upper, item)
    merged = lower[:-1] + upper[:-1]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in merged:
        pid = item[2]["id"]
        if pid in seen:
            continue
        seen.add(pid)
        out.append(item[2])
    return out if out else list(pois)


def diameter_pairwise_km(pois: list[dict[str, Any]]) -> float:
    if len(pois) < 2:
        return 0.0
    best = 0.0
    for i in range(len(pois)):
        pi = pois[i]
        for j in range(i + 1, len(pois)):
            d = haversine_km(pi["lat"], pi["lon"], pois[j]["lat"], pois[j]["lon"])
            if d > best:
                best = d
    return best


def diameter_km(
    pois: list[dict[str, Any]],
    pairwise_max_n: int = PAIRWISE_DIAMETER_MAX_N,
) -> float:
    """Exact haversine diameter. Pairwise if n is small; else pairwise on convex hull."""
    n = len(pois)
    if n < 2:
        return 0.0
    if n <= pairwise_max_n:
        return diameter_pairwise_km(pois)
    hull = _convex_hull_pois(pois)
    return diameter_pairwise_km(hull)


def _diameter_km(pois: list[dict[str, Any]]) -> float:
    return diameter_km(pois)


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


def _parse_hub_ids(raw: Any) -> list[str] | None:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, list):
        return None
    return [str(x) for x in parsed]


def _cluster_row_same(
    row: sqlite3.Row,
    hub_ids: list[str],
    title: str,
    center_lat: float,
    center_lon: float,
) -> bool:
    stored_ids = _parse_hub_ids(row["hub_ids"])
    if stored_ids != hub_ids:
        return False
    if (row["title"] or "") != title:
        return False
    plat = row["center_lat"]
    plon = row["center_lon"]
    if plat is None or plon is None:
        return False
    return abs(float(plat) - center_lat) <= _CENTER_EPS and abs(float(plon) - center_lon) <= _CENTER_EPS


def persist_clusters(
    conn: sqlite3.Connection,
    places: list[dict[str, Any]],
    radius_km: int,
    cap: int | None = None,
) -> int:
    """Write live discs so POST /api/price can load the clicked cluster_id.

    Writes ranked[:cap] plus any ranked cluster already stored for this radius.
    INSERT OR REPLACE only when the row is missing or hub_ids/title/center changed.
    """
    radius_i = int(radius_km)
    if cap is None:
        cap = len(places)
    else:
        cap = max(0, int(cap))
    existing_rows = conn.execute(
        "SELECT id, hub_ids, title, center_lat, center_lon FROM cluster WHERE radius_km = ?",
        (radius_i,),
    ).fetchall()
    existing = {str(r["id"]): r for r in existing_rows}
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for place in places[:cap]:
        cid = place["cluster_id"]
        if cid in seen:
            continue
        seen.add(cid)
        chosen.append(place)
    if cap < len(places):
        for place in places[cap:]:
            cid = place["cluster_id"]
            if cid in seen:
                continue
            if cid in existing:
                seen.add(cid)
                chosen.append(place)
    sql = (
        "INSERT OR REPLACE INTO cluster("
        "id, radius_km, hub_ids, title, center_lat, center_lon, diameter_km, ingredient_mask"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    writes = 0
    for place in chosen:
        hub_ids = [h["hub_id"] for h in place["hubs"]]
        title = place.get("title") or ""
        clat = float(place["center"]["lat"])
        clon = float(place["center"]["lon"])
        prev = existing.get(place["cluster_id"])
        if prev is not None and _cluster_row_same(prev, hub_ids, title, clat, clon):
            continue
        conn.execute(
            sql,
            (
                place["cluster_id"],
                radius_i,
                json.dumps(hub_ids, ensure_ascii=False),
                title,
                clat,
                clon,
                float(place.get("diameter_km") or 0.0),
                json.dumps(place.get("coverage") or {}, ensure_ascii=True),
            ),
        )
        writes += 1
    if writes:
        conn.commit()
    return writes


def list_places(
    conn: sqlite3.Connection,
    ingredients: list[str],
    radius_km: int,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    hubs = load_hubs(conn)
    pois = load_pois(conn)
    burger = set(ingredients)
    indexed = index_pois_by_hub([p for p in pois if p["ingredient_id"] in burger])
    raw: list[dict[str, Any]] = []
    for hub_set in iter_candidates(hubs, float(radius_km)):
        place = build_place(hub_set, pois_for_hubs(indexed, hub_set), ingredients, radius_km)
        if place is not None:
            raw.append(place)
    ranked = rank_places(raw, ingredients, radius_km)
    cap = max(0, int(limit))
    persist_clusters(conn, ranked, radius_km, cap=cap)
    return {"total_found": len(ranked), "places": ranked[:cap]}


def benchmark_list_places(
    conn: sqlite3.Connection,
    ingredients: list[str],
    radius_km: int,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Time list_places on the open connection. For golden fixtures, not live 8MB db."""
    hubs = load_hubs(conn)
    pois = load_pois(conn)
    n_cand = len(iter_candidates(hubs, float(radius_km)))
    t0 = time.perf_counter()
    out = list_places(conn, ingredients, radius_km, limit)
    ms = (time.perf_counter() - t0) * 1000.0
    return {
        "hubs": len(hubs),
        "pois": len(pois),
        "candidates": n_cand,
        "ms": round(ms, 3),
        "total_found": out["total_found"],
    }
