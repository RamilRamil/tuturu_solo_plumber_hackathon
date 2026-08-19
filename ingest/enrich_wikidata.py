"""D4: Wikidata P571 / labels. Match OSM wikidata tag, else ~100 m."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.common import DB_DEFAULT, dump_json, load_ingredient_rules, now_iso, parse_start_date

from lib.models import connect

SPARQL = "https://query.wikidata.org/sparql"
UA = "burger-hackathon-ingest/0.1"
MATCH_M = 100.0
EARTH_M = 6371000.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(a)))


def _sparql(query: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    last: Exception | None = None
    for attempt in range(4):
        req = urllib.request.Request(
            SPARQL + "?" + params,
            headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
            rows = doc.get("results", {}).get("bindings", [])
            out: list[dict[str, Any]] = []
            for row in rows:
                item: dict[str, Any] = {}
                for k, v in row.items():
                    if isinstance(v, dict):
                        item[k] = v.get("value")
                out.append(item)
            return out
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                wait_s = 65 * (attempt + 1)
                print("d4 sparql 429 wait=%ss" % wait_s, flush=True)
                time.sleep(wait_s)
                continue
            raise
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            last = exc
            time.sleep(5.0 * float(attempt + 1))
    if last is not None:
        raise last
    return []


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _parse_point(wkt: str) -> Optional[tuple[float, float]]:
    # Point(lon lat)
    if not wkt:
        return None
    s = wkt.replace("Point(", "").replace(")", "").strip()
    parts = s.split()
    if len(parts) < 2:
        return None
    try:
        return float(parts[1]), float(parts[0])
    except ValueError:
        return None


def fetch_class(
    qid: str,
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    lon_min: Optional[float] = None,
    lon_max: Optional[float] = None,
) -> list[dict[str, Any]]:
    bbox = ""
    if None not in (lat_min, lat_max, lon_min, lon_max):
        bbox = (
            "  FILTER(geof:latitude(?coord) >= %s && geof:latitude(?coord) <= %s"
            " && geof:longitude(?coord) >= %s && geof:longitude(?coord) <= %s)\n"
            % (lat_min, lat_max, lon_min, lon_max)
        )
    query = (
        "PREFIX geof: <http://www.opengis.net/def/function/geosparql/>\n"
        "SELECT ?x ?xLabel ?coord ?inception WHERE {\n"
        "  ?x wdt:P31/wdt:P279* wd:%s ;\n"
        "     wdt:P17 wd:Q159 ;\n"
        "     wdt:P625 ?coord .\n"
        "  OPTIONAL { ?x wdt:P571 ?inception }\n"
        "%s"
        "  SERVICE wikibase:label { bd:serviceParam wikibase:language \"ru,en\" }\n"
        "}\n"
    ) % (qid, bbox)
    try:
        return _sparql(query)
    except Exception as exc:
        print("d4 sparql fail class=%s err=%s" % (qid, exc), flush=True)
        return []


def live_db_default() -> Path:
    parts = _ROOT.parts
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        return Path(*parts[:idx]) / "data" / "burger.db"
    return DB_DEFAULT


def run_d4(
    db_path: Path,
    only_ingredient: Optional[str] = None,
    bbox: Optional[tuple[float, float, float, float]] = None,
) -> dict[str, Any]:
    rules = load_ingredient_rules()
    classes: list[str] = []
    for item in rules:
        if only_ingredient and item.get("id") != only_ingredient:
            continue
        for q in item.get("wikidata_classes") or []:
            q = q.strip()
            if q and q not in classes:
                classes.append(q)
    by_qid: dict[str, dict[str, Any]] = {}
    coord_index: list[tuple[str, float, float, Optional[int]]] = []
    lat_min = lon_min = lat_max = lon_max = None
    if bbox:
        lat_min, lat_max, lon_min, lon_max = bbox
    for i, qid in enumerate(classes):
        if i:
            time.sleep(65)
        rows = fetch_class(qid, lat_min, lat_max, lon_min, lon_max)
        print("d4 class=%s rows=%s" % (qid, len(rows)), flush=True)
        for row in rows:
            uri = row.get("x") or ""
            key = _qid(uri)
            inception = row.get("inception")
            year = None
            if inception:
                y, _t = parse_start_date(inception[:4] if len(inception) >= 4 else inception)
                year = y
            pt = _parse_point(row.get("coord") or "")
            by_qid[key] = {"label": row.get("xLabel"), "year": year, "coord": pt}
            if pt:
                coord_index.append((key, pt[0], pt[1], year))
    conn = connect(db_path)
    if only_ingredient:
        pois = conn.execute(
            "SELECT id, lat, lon, wikidata, start_date_from, start_date_to, name FROM poi WHERE ingredient_id = ?",
            (only_ingredient,),
        ).fetchall()
    else:
        pois = conn.execute(
            "SELECT id, lat, lon, wikidata, start_date_from, start_date_to, name FROM poi"
        ).fetchall()
    tagged = 0
    by_coord = 0
    dated = 0
    for poi in pois:
        qid = None
        wd = poi["wikidata"] or ""
        if wd.startswith("Q"):
            qid = wd.split(";")[0].strip()
        elif wd.startswith("http"):
            qid = _qid(wd)
        hit = by_qid.get(qid) if qid else None
        if hit:
            tagged += 1
        else:
            best = None
            best_d = MATCH_M + 1
            for key, lat, lon, year in coord_index:
                d = _haversine_m(poi["lat"], poi["lon"], lat, lon)
                if d < best_d:
                    best_d = d
                    best = (key, year)
            if best is not None and best_d <= MATCH_M:
                hit = {"year": best[1], "qid": best[0]}
                by_coord += 1
                conn.execute("UPDATE poi SET wikidata = ? WHERE id = ?", (best[0], poi["id"]))
        if hit and hit.get("year") and poi["start_date_from"] is None:
            conn.execute(
                "UPDATE poi SET start_date_from = ?, start_date_to = COALESCE(start_date_to, ?) WHERE id = ?",
                (hit["year"], hit["year"], poi["id"]),
            )
            dated += 1
    conn.commit()
    conn.close()
    return {
        "classes": classes,
        "ingredient": only_ingredient,
        "bbox": list(bbox) if bbox else None,
        "wikidata_rows": len(by_qid),
        "matched_tag": tagged,
        "matched_coord": by_coord,
        "inception_filled": dated,
        "poi_scanned": len(pois),
        "at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(live_db_default()))
    parser.add_argument("--ingredient", default="")
    parser.add_argument(
        "--bbox",
        default="",
        help="lat_min,lat_max,lon_min,lon_max (Yaroslavl oblast ~ 56.5,59.2,37.2,41.6)",
    )
    args = parser.parse_args()
    db_path = Path(args.db).resolve()
    if "/.worktrees/data/" in str(db_path):
        print("refusing data-worktree burger.db", flush=True)
        return 2
    bbox = None
    if args.bbox.strip():
        parts = [float(x.strip()) for x in args.bbox.split(",")]
        if len(parts) != 4:
            print("bbox needs lat_min,lat_max,lon_min,lon_max", flush=True)
            return 2
        bbox = (parts[0], parts[1], parts[2], parts[3])
    only = args.ingredient.strip() or None
    summary = run_d4(db_path, only_ingredient=only, bbox=bbox)
    summary["db"] = str(db_path)
    dump_json(_ROOT / "data" / "d4_ancient_temple_summary.json", summary)
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
