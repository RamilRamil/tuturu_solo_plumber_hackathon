"""D3: POI from OSM via package osmium (not pyosmium on PyPI)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.common import (
    COVERAGE_PATH,
    DB_DEFAULT,
    PBF_DIR,
    POI_ATTACH_FALLBACK_KM,
    POI_ATTACH_KM,
    dump_json,
    haversine_km,
    hours_status,
    load_ingredient_rules,
    match_ingredient,
    now_iso,
    parse_start_date,
    significance,
)

from lib.models import connect

# G7 regional extract (Yaroslavl oblast). Do not fetch russia-latest.
PBF_URL = (
    "https://download.openstreetmap.fr/extracts/russia/"
    "central_federal_district/yaroslavl_oblast-latest.osm.pbf"
)
PBF_NAME = "yaroslavl_oblast-latest.osm.pbf"
REGION_LABEL = "Yaroslavl oblast"


def ensure_pbf(dest_dir: Path = PBF_DIR) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / PBF_NAME
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    print("d3 downloading %s" % PBF_URL, flush=True)
    tmp = path.with_suffix(".pbf.part")
    req = urllib.request.Request(PBF_URL, headers={"User-Agent": "burger-hackathon-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(path)
    print("d3 pbf bytes=%s" % path.stat().st_size, flush=True)
    return path


def _tags_of(obj: Any) -> dict[str, str]:
    return {t.k: t.v for t in obj.tags}


def _centroid(locations: list[Any]) -> Optional[tuple[float, float]]:
    if not locations:
        return None
    lat = sum(loc.lat for loc in locations) / len(locations)
    lon = sum(loc.lon for loc in locations) / len(locations)
    return lat, lon


class PoiHandler:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        import osmium

        class _H(osmium.SimpleHandler):
            def __init__(self, outer: "PoiHandler") -> None:
                super().__init__()
                self.outer = outer

            def node(self, n: Any) -> None:
                self.outer._on_node(n)

            def way(self, w: Any) -> None:
                self.outer._on_way(w)

            def relation(self, r: Any) -> None:
                self.outer._on_relation(r)

        self._osmium = osmium
        self.rules = rules
        self.pois: list[dict[str, Any]] = []
        self.admin4: set[str] = set()
        self.handler = _H(self)

    def _note_admin(self, tags: dict[str, str]) -> None:
        if tags.get("boundary") == "administrative" and tags.get("admin_level") == "4":
            name = (tags.get("name:ru") or tags.get("name") or "").strip()
            if name:
                self.admin4.add(name)

    def _add(self, osm_type: str, osm_id: int, lat: float, lon: float, tags: dict[str, str]) -> None:
        ingredient = match_ingredient(tags, self.rules)
        if not ingredient:
            return
        raw = tags.get("start_date")
        date_from, date_to = parse_start_date(raw)
        has_start = date_from is not None or date_to is not None
        poi_id = "%s-%s-%s" % (osm_type[0], osm_id, ingredient)
        self.pois.append(
            {
                "id": poi_id,
                "osm_type": osm_type,
                "osm_id": int(osm_id),
                "lat": float(lat),
                "lon": float(lon),
                "name": tags.get("name"),
                "ingredient_id": ingredient,
                "wikidata": tags.get("wikidata"),
                "wikipedia": tags.get("wikipedia"),
                "start_date_raw": raw,
                "start_date_from": date_from,
                "start_date_to": date_to,
                "opening_hours": tags.get("opening_hours"),
                "hours_status": hours_status(tags.get("opening_hours")),
                "significance": significance(tags, has_start),
                "tags_json": json.dumps(tags, ensure_ascii=True),
                "hub_id": None,
            }
        )

    def _on_node(self, n: Any) -> None:
        if not n.tags:
            return
        tags = _tags_of(n)
        self._note_admin(tags)
        if not n.location.valid():
            return
        self._add("node", n.id, n.location.lat, n.location.lon, tags)

    def _on_way(self, w: Any) -> None:
        if not w.tags:
            return
        tags = _tags_of(w)
        self._note_admin(tags)
        if match_ingredient(tags, self.rules) is None:
            return
        try:
            locs = [n.location for n in w.nodes if n.location.valid()]
        except self._osmium.InvalidLocationError:
            return
        cen = _centroid(locs)
        if cen is None:
            return
        self._add("way", w.id, cen[0], cen[1], tags)

    def _on_relation(self, r: Any) -> None:
        if not r.tags:
            return
        tags = _tags_of(r)
        self._note_admin(tags)

    def apply(self, pbf_path: Path) -> None:
        self.handler.apply_file(str(pbf_path), locations=True)


def _load_hubs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT id, subject, lat, lon FROM hub").fetchall()
    return [
        {"id": r["id"], "subject": r["subject"], "lat": float(r["lat"]), "lon": float(r["lon"])}
        for r in rows
    ]


def attach_hubs(pois: list[dict[str, Any]], hubs: list[dict[str, Any]]) -> None:
    if not hubs:
        return
    for poi in pois:
        best: Optional[dict[str, Any]] = None
        best_d = 1e9
        for hub in hubs:
            d = haversine_km(poi["lat"], poi["lon"], hub["lat"], hub["lon"])
            if d < best_d:
                best_d = d
                best = hub
        if best is not None and best_d <= POI_ATTACH_KM:
            poi["hub_id"] = best["id"]
            continue
        fallback: Optional[dict[str, Any]] = None
        fallback_d = 1e9
        for hub in hubs:
            d = haversine_km(poi["lat"], poi["lon"], hub["lat"], hub["lon"])
            if d < fallback_d:
                fallback_d = d
                fallback = hub
        if fallback is not None and fallback_d <= POI_ATTACH_FALLBACK_KM:
            poi["hub_id"] = fallback["id"]


def _insert_pois(conn: sqlite3.Connection, pois: list[dict[str, Any]]) -> None:
    conn.execute("DELETE FROM poi")
    conn.executemany(
        """
        INSERT INTO poi(
          id, osm_type, osm_id, lat, lon, name, ingredient_id, wikidata, wikipedia,
          start_date_raw, start_date_from, start_date_to, opening_hours, hours_status,
          significance, tags_json, hub_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                p["id"],
                p["osm_type"],
                p["osm_id"],
                p["lat"],
                p["lon"],
                p["name"],
                p["ingredient_id"],
                p["wikidata"],
                p["wikipedia"],
                p["start_date_raw"],
                p["start_date_from"],
                p["start_date_to"],
                p["opening_hours"],
                p["hours_status"],
                p["significance"],
                p["tags_json"],
                p["hub_id"],
            )
            for p in pois
        ],
    )


def run_d3(db_path: Path, pbf_path: Optional[Path] = None) -> dict[str, Any]:
    try:
        import osmium  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("package osmium is required (pip install osmium, not pyosmium)") from exc
    path = pbf_path or ensure_pbf()
    rules = load_ingredient_rules()
    handler = PoiHandler(rules)
    handler.apply(path)
    conn = connect(db_path)
    hubs = _load_hubs(conn)
    attach_hubs(handler.pois, hubs)
    _insert_pois(conn, handler.pois)
    conn.commit()
    attached = sum(1 for p in handler.pois if p.get("hub_id"))
    by_ing: dict[str, int] = {}
    for p in handler.pois:
        by_ing[p["ingredient_id"]] = by_ing.get(p["ingredient_id"], 0) + 1
    coverage = {
        "regions_loaded": [REGION_LABEL],
        "admin_level_4": sorted(handler.admin4),
        "pbf": str(path),
        "pbf_bytes": path.stat().st_size,
        "poi_count": len(handler.pois),
        "poi_attached": attached,
        "by_ingredient": by_ing,
        "hubs_seen": len(hubs),
        "at": now_iso(),
        "note": "wave1 D3 uses Yaroslavl oblast extract (G7); not russia-latest",
    }
    dump_json(COVERAGE_PATH, coverage)
    conn.close()
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DB_DEFAULT))
    parser.add_argument("--pbf", default="")
    args = parser.parse_args()
    pbf = Path(args.pbf) if args.pbf else None
    coverage = run_d3(Path(args.db), pbf)
    print(coverage, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
