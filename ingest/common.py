"""Shared ingest helpers. ASCII literals only."""

from __future__ import annotations

import json
import math
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.models import make_hub_id
from lib.tutu_mcp import extract_meta, price_is_absent, unwrap_tool_result

CITIES_PATH = ROOT / "data" / "cities_ru.json"
ALIASES_PATH = ROOT / "data" / "city_aliases.json"
INGREDIENTS_PATH = ROOT / "ingredients.yaml"
DB_DEFAULT = ROOT / "data" / "burger.db"
PBF_DIR = ROOT / "data" / "osm"
COVERAGE_PATH = ROOT / "data" / "coverage.json"
WAVE1_SUMMARY_PATH = ROOT / "data" / "wave1_summary.json"
SOFTFAIL_PATH = ROOT / "data" / "softfail_log.json"

WAVE1_KM = 400.0
LEG_KM = 150.0
POI_ATTACH_KM = 50.0
POI_ATTACH_FALLBACK_KM = 150.0
PRODUCT_CONCURRENCY = 4
CALL_TIMEOUT_S = 30
ORIGIN_NAME = "\u041c\u043e\u0441\u043a\u0432\u0430"
ORIGIN_SUBJECT = "\u041c\u043e\u0441\u043a\u0432\u0430"

# B1 p.4 regression labels (name or resolved_name).
REGRESSION_LABELS = (
    "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u043b\u044c",
    "\u0420\u043e\u0441\u0442\u043e\u0432 \u0412\u0435\u043b\u0438\u043a\u0438\u0439",
    "\u0420\u044f\u0437\u0430\u043d\u044c",
    "\u041a\u043e\u043b\u043e\u043c\u043d\u0430",
    "\u0422\u0443\u043b\u0430",
    "\u041a\u0430\u043b\u0443\u0433\u0430",
    "\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440",
    "\u0418\u0432\u0430\u043d\u043e\u0432\u043e",
)

# G7: do not ingest ruins=yes (inflates vs field-test §12).
SKIP_OSM_RULES = frozenset({"ruins=yes"})

EARTH_KM = 6371.0


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def weekday_plus_weeks(weeks: int = 3, today: Optional[date] = None) -> str:
    d = (today or date.today()) + timedelta(weeks=weeks)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def load_cities(path: Path = CITIES_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def wave1_cities(cities: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    rows = cities if cities is not None else load_cities()
    picked = [c for c in rows if float(c.get("dM") or 0) <= WAVE1_KM]
    picked.sort(key=lambda c: float(c.get("dM") or 0))
    return picked


def origin_hub_id() -> str:
    return make_hub_id(ORIGIN_NAME, ORIGIN_SUBJECT)


def hub_id_of(city: dict[str, Any]) -> str:
    return make_hub_id(str(city["name"]), str(city["subject"]))


def parse_start_date(raw: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not raw:
        return None, None
    s = str(raw).strip()
    m = re.match(r"^(\d{3,4})\s*\.\.\s*(\d{3,4})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d{3,4})\s*-\s*(\d{3,4})$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(?:after|from|since|before)\s+(\d{3,4})$", s, re.I)
    if m:
        y = int(m.group(1))
        if s.lower().startswith("before"):
            return None, y
        return y, None
    m = re.match(r"^C(\d{1,2})$", s, re.I)
    if m:
        century = int(m.group(1))
        return (century - 1) * 100 + 1, century * 100
    m = re.match(r"^~?\s*(\d{3,4})$", s)
    if m:
        y = int(m.group(1))
        return y, y
    m = re.search(r"(\d{3,4})", s)
    if m:
        y = int(m.group(1))
        return y, y
    return None, None


def hours_status(opening_hours: Optional[str]) -> str:
    if not opening_hours:
        return "unknown"
    n = opening_hours.strip().casefold()
    if n in ("off", "closed") or n.startswith("closed") or n == "24/7 off":
        return "closed"
    return "open"


def significance(tags: dict[str, str], has_start: bool) -> float:
    return (
        3.0 * (1.0 if tags.get("wikidata") else 0.0)
        + 2.0 * (1.0 if tags.get("wikipedia") else 0.0)
        + 2.0 * (1.0 if has_start else 0.0)
        + 1.0 * (1.0 if tags.get("name") else 0.0)
        + min(len(tags) / 5.0, 2.0)
    )


def load_ingredient_rules(path: Path = INGREDIENTS_PATH) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    in_osm = False
    in_ingredients = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        if stripped == "ingredients:":
            in_ingredients = True
            continue
        if stripped and not stripped.startswith(" ") and stripped.endswith(":"):
            in_ingredients = False
            if current is not None:
                items.append(current)
                current = None
            in_osm = False
            continue
        if not in_ingredients:
            continue
        if stripped.startswith("  - id:"):
            if current is not None:
                items.append(current)
            current = {
                "id": stripped.split(":", 1)[1].strip(),
                "osm": [],
                "require_name": False,
                "wikidata_classes": [],
            }
            in_osm = False
            continue
        if current is None:
            continue
        body = stripped.strip()
        if body.startswith("require_name:"):
            current["require_name"] = "true" in body.lower()
            in_osm = False
            continue
        if body == "osm:":
            in_osm = True
            continue
        if in_osm and body.startswith("- "):
            rule = body[2:].strip().strip('"').strip("'")
            if rule and rule not in SKIP_OSM_RULES:
                current["osm"].append(rule)
            continue
        if body.startswith("wikidata_classes:"):
            in_osm = False
            blob = body.split(":", 1)[1].strip().strip("[]")
            current["wikidata_classes"] = [p.strip() for p in blob.split(",") if p.strip()]
            continue
        if not stripped.startswith("      "):
            in_osm = False
    if current is not None:
        items.append(current)
    return items


def _clause_ok(tags: dict[str, str], clause: str) -> bool:
    clause = clause.strip()
    if not clause:
        return False
    if clause == "name":
        return bool((tags.get("name") or "").strip())
    if "=" not in clause:
        return clause in tags
    key, vals = clause.split("=", 1)
    got = tags.get(key)
    if got is None:
        return False
    allowed = set(vals.split("|"))
    return got in allowed


def match_ingredient(tags: dict[str, str], rules: list[dict[str, Any]]) -> Optional[str]:
    for item in rules:
        for rule in item["osm"]:
            parts = [p.strip() for p in rule.split("+")]
            if all(_clause_ok(tags, p) for p in parts):
                if item.get("require_name") and not (tags.get("name") or "").strip():
                    continue
                return str(item["id"])
    return None


def min_duration_min(doc: Any) -> Optional[int]:
    if not isinstance(doc, dict):
        return None
    durs: list[int] = []
    meta = extract_meta(doc)
    summary = meta.get("modes_summary") or {}
    if isinstance(summary, dict):
        for info in summary.values():
            if not isinstance(info, dict):
                continue
            raw = info.get("min_duration_min")
            if raw is None:
                continue
            try:
                n = int(raw)
            except (TypeError, ValueError):
                continue
            if n > 0:
                durs.append(n)
    for key in ("variants", "offers"):
        rows = doc.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw = row.get("duration_min")
            if raw is None:
                continue
            try:
                n = int(raw)
            except (TypeError, ValueError):
                continue
            if n > 0:
                durs.append(n)
    return min(durs) if durs else None


def log_mode_softfail(payload: Any, sink: list[dict[str, Any]], context: str) -> None:
    doc = unwrap_tool_result(payload)
    if not isinstance(doc, dict):
        return
    meta = extract_meta(payload)
    requested = meta.get("modes_requested") or doc.get("modes_requested")
    summary = meta.get("modes_summary")
    if not requested or not isinstance(summary, dict):
        return
    if isinstance(requested, str):
        req = {p.strip() for p in requested.split(",") if p.strip()}
    elif isinstance(requested, list):
        req = {str(x) for x in requested}
    else:
        return
    got = {str(k) for k in summary.keys()}
    if req and got and req != got:
        sink.append(
            {
                "context": context,
                "requested": sorted(req),
                "summary_keys": sorted(got),
                "at": now_iso(),
            }
        )


def query_label(resolved_name: Optional[str], name: str) -> str:
    if resolved_name and resolved_name.strip():
        return resolved_name.strip()
    return name


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
