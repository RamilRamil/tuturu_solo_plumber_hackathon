"""Phase-2 price planning. Guard and MCP come from lib.tutu_mcp (import only)."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Iterator, Optional

from lib.tutu_mcp import (
    CALL_TIMEOUT_S,
    MAX_CONCURRENCY,
    TutuMcp,
    check_resolve,
    load_aliases,
    normalize,
    price_is_absent,
)

PRICE_STATUS = "fixture-confirmed"
CURRENCY = "RUB"
FIRST_LEG_PAUSE_S = 3.0
EVENT_PAUSE_S = 1.0
DEFAULT_DB = "data/burger.db"
ASCII_ORIGIN_GEO = {"moscow": "fixture-mow", "moskva": "fixture-mow"}


class UnknownCluster(Exception):
    """cluster_id is not in table cluster (HTTP 404, not SSE warning)."""


def db_path() -> str:
    return os.environ.get("BURGER_DB") or DEFAULT_DB


def live_tutu_enabled() -> bool:
    flag = (os.environ.get("BURGER_LIVE_TUTU") or "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def open_mcp(path: Optional[str] = None) -> TutuMcp:
    return TutuMcp(
        path or db_path(),
        timeout_s=CALL_TIMEOUT_S,
        max_concurrency=MAX_CONCURRENCY,
    )


def load_cluster_row(conn: sqlite3.Connection, cluster_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, hub_ids, title FROM cluster WHERE id = ? LIMIT 1",
        (cluster_id,),
    ).fetchone()
    if row is None:
        raise UnknownCluster(cluster_id)
    return row


def parse_hub_ids(raw: str) -> list[str]:
    data = json.loads(raw)
    return [str(x) for x in data]


def hub_row(conn: sqlite3.Connection, hub_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM hub WHERE id = ?", (hub_id,)).fetchone()


def match_origin_hub(conn: sqlite3.Connection, origin: str) -> Optional[sqlite3.Row]:
    q = normalize(origin)
    hubs = list(conn.execute("SELECT * FROM hub"))
    aliases = load_aliases()
    for row in hubs:
        names = [row["name"] or "", row["resolved_name"] or "", row["id"].split("|")[0]]
        if any(normalize(n) == q for n in names if n):
            return row
        for alias in aliases.get(row["id"], []):
            if normalize(alias) == q:
                return row
    geo = ASCII_ORIGIN_GEO.get(q)
    if geo:
        for row in hubs:
            if (row["tutu_geo_id"] or "") == geo:
                return row
    return None


def guard_status(meta: dict[str, Any], expected_name: str, expected_region: str) -> str:
    ok, _reason = check_resolve(meta, expected_name, expected_region)
    return "ok" if ok else "misresolved"


def meta_from_hub(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "to": {
            "name": row["resolved_name"] or row["name"],
            "region": row["resolved_region"] or row["expected_region"] or "",
            "geo_id": row["tutu_geo_id"],
        }
    }


def first_window_start(month: str) -> str:
    year_s, mon_s = month.split("-")
    year, mon = int(year_s), int(mon_s)
    last = monthrange(year, mon)[1]
    day = 9 if last >= 9 else 1
    return date(year, mon, day).isoformat()


def later_window_starts(month: str, first: str) -> list[str]:
    year_s, mon_s = month.split("-")
    year, mon = int(year_s), int(mon_s)
    last = monthrange(year, mon)[1]
    out: list[str] = []
    start = date.fromisoformat(first)
    cursor = start + timedelta(days=7)
    while cursor.month == mon and cursor.day <= last:
        out.append(cursor.isoformat())
        cursor += timedelta(days=7)
    return out


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def dist_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def directed_leg(
    conn: sqlite3.Connection,
    origin_hub: str,
    dest_hub: str,
    date_probed: str,
) -> Optional[sqlite3.Row]:
    row = conn.execute(
        """
        SELECT * FROM leg
        WHERE origin_hub = ? AND dest_hub = ? AND date_probed = ?
        """,
        (origin_hub, dest_hub, date_probed),
    ).fetchone()
    if row is not None:
        return row
    return conn.execute(
        """
        SELECT * FROM leg
        WHERE origin_hub = ? AND dest_hub = ?
        ORDER BY date_probed
        """,
        (origin_hub, dest_hub),
    ).fetchone()


def route_cache_payload(
    conn: sqlite3.Connection,
    origin_hub: str,
    dest_hub: str,
    day: str,
) -> Optional[dict[str, Any]]:
    row = conn.execute(
        """
        SELECT payload_json FROM route_cache
        WHERE origin_hub = ? AND dest_hub = ? AND date = ?
        """,
        (origin_hub, dest_hub, day),
    ).fetchone()
    if row is None:
        return None
    raw = row["payload_json"]
    if isinstance(raw, str):
        return json.loads(raw)
    return raw if isinstance(raw, dict) else None


def hotel_cache_row(
    conn: sqlite3.Connection,
    hub_id: str,
    check_in: str,
    check_out: str,
    adults: int,
) -> Optional[sqlite3.Row]:
    row = conn.execute(
        """
        SELECT * FROM hotel_cache
        WHERE hub_id = ? AND check_in = ? AND check_out = ? AND adults = ?
        """,
        (hub_id, check_in, check_out, adults),
    ).fetchone()
    if row is not None:
        return row
    return conn.execute(
        "SELECT * FROM hotel_cache WHERE hub_id = ? AND adults = ? ORDER BY check_in",
        (hub_id, adults),
    ).fetchone()


def stay_total_from_hotel_payload(payload: dict[str, Any]) -> Optional[int]:
    hotels = payload.get("hotels") if isinstance(payload, dict) else None
    if not isinstance(hotels, list) or not hotels:
        return None
    offer = hotels[0]
    if not isinstance(offer, dict):
        return None
    amount = offer.get("min_price")
    if amount is None and isinstance(offer.get("stay"), dict):
        amount = offer["stay"].get("stay_total")
    if price_is_absent(amount):
        return None
    return int(float(amount))


def nights_from_hotel_payload(payload: dict[str, Any], fallback: int) -> int:
    hotels = payload.get("hotels") if isinstance(payload, dict) else None
    if isinstance(hotels, list) and hotels and isinstance(hotels[0], dict):
        stay = hotels[0].get("stay")
        if isinstance(stay, dict) and stay.get("nights"):
            return int(stay["nights"])
    return fallback


def checkout_url_from_obj(obj: Any) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    url = obj.get("checkout_url")
    if isinstance(url, str) and url:
        return url
    return None


def pick_mode(modes: str) -> str:
    parts = [p for p in (modes or "").split(",") if p]
    return parts[0] if parts else ""


def sort_hubs_from_origin(
    origin: sqlite3.Row,
    hubs: list[sqlite3.Row],
) -> list[sqlite3.Row]:
    return sorted(
        hubs,
        key=lambda h: dist_km(origin["lat"], origin["lon"], h["lat"], h["lon"]),
    )


def order_visit(
    conn: sqlite3.Connection,
    origin: sqlite3.Row,
    cluster_hubs: list[sqlite3.Row],
    day: str,
) -> list[sqlite3.Row]:
    remaining = list(cluster_hubs)
    ordered: list[sqlite3.Row] = []
    current_id = origin["id"]
    while remaining:
        sellable: list[sqlite3.Row] = []
        blocked: list[sqlite3.Row] = []
        for h in remaining:
            row = directed_leg(conn, current_id, h["id"], day)
            if (
                row is not None
                and row["status"] == "ok"
                and not price_is_absent(row["min_price"])
            ):
                sellable.append(h)
            else:
                blocked.append(h)
        pool = sellable if sellable else blocked
        current = hub_row(conn, current_id) or origin
        nxt = sort_hubs_from_origin(current, pool)[0]
        ordered.append(nxt)
        remaining = [h for h in remaining if h["id"] != nxt["id"]]
        current_id = nxt["id"]
    return ordered


def warning_event(
    code: str,
    message: str,
    hub_id: Optional[str] = None,
    from_hub: str = "",
    to_hub: str = "",
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "hub_id": hub_id,
        "leg": {"from_hub": from_hub, "to_hub": to_hub},
    }


def iter_price_events(req: dict[str, Any], mcp: TutuMcp) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (event_name, payload). Caller must pause between frames."""
    conn = mcp.conn
    cluster = load_cluster_row(conn, req["cluster_id"])
    cluster_ids = parse_hub_ids(cluster["hub_ids"])
    cluster_hubs = [hub_row(conn, hid) for hid in cluster_ids]
    if any(h is None for h in cluster_hubs):
        raise UnknownCluster(req["cluster_id"])
    cluster_hubs = [h for h in cluster_hubs if h is not None]

    origin_row = match_origin_hub(conn, req["origin"])
    origin_guard = "misresolved"
    origin_meta = {"to": {"name": "", "region": "", "geo_id": None}}
    if origin_row is not None:
        origin_meta = meta_from_hub(origin_row)
        origin_guard = guard_status(
            origin_meta,
            origin_row["name"],
            origin_row["expected_region"] or origin_row["subject"],
        )

    hub_guards: list[dict[str, Any]] = []
    hub_warnings: list[dict[str, Any]] = []
    for h in cluster_hubs:
        st = guard_status(
            meta_from_hub(h),
            h["name"],
            h["expected_region"] or h["subject"],
        )
        hub_guards.append(
            {
                "hub_id": h["id"],
                "query": h["name"],
                "name": h["resolved_name"] or h["name"],
                "region": h["resolved_region"] or h["expected_region"] or "",
                "guard": st,
            }
        )
        if st != "ok":
            hub_warnings.append(
                warning_event(
                    "misresolved",
                    "guard rejected destination",
                    hub_id=h["id"],
                )
            )

    geo_id = None
    if origin_row is not None:
        geo_id = origin_row["tutu_geo_id"]
    yield (
        "resolved",
        {
            "origin": {
                "query": req["origin"],
                "name": (origin_row["resolved_name"] if origin_row else req["origin"]),
                "region": (
                    (origin_row["resolved_region"] or origin_row["expected_region"])
                    if origin_row
                    else ""
                ),
                "geo_id": geo_id,
                "guard": origin_guard if origin_row is not None else "misresolved",
            },
            "hubs": hub_guards,
        },
    )

    for w in hub_warnings:
        yield ("warning", w)
    if origin_row is None or origin_guard != "ok":
        yield (
            "warning",
            warning_event("misresolved", "guard rejected origin"),
        )

    if origin_row is None or origin_guard != "ok":
        yield (
            "done",
            {
                "ok": True,
                "cluster_id": req["cluster_id"],
                "price_status": PRICE_STATUS,
            },
        )
        return

    window0 = first_window_start(req["month"])
    visit = order_visit(conn, origin_row, cluster_hubs, window0)
    return_date = add_days(window0, max(0, int(req["days"]) - 1))
    priced = False
    transport_total = 0
    lodging_total = 0
    checkout_items: list[dict[str, Any]] = []
    first_leg_sent = False
    hops: list[tuple[sqlite3.Row, sqlite3.Row, str]] = []
    current = origin_row
    for dest in visit:
        hops.append((current, dest, window0 if current["id"] == origin_row["id"] else window0))
        current = dest
    hops.append((current, origin_row, return_date))

    seen_return = False
    for idx, (frm, to, day) in enumerate(hops):
        is_return = to["id"] == origin_row["id"]
        row = directed_leg(conn, frm["id"], to["id"], day)
        if is_return:
            seen_return = True
            if row is None or row["status"] != "ok" or price_is_absent(row["min_price"]):
                prev = hops[idx - 1][0] if idx > 0 else None
                if prev is not None and prev["id"] != frm["id"]:
                    alt = directed_leg(conn, prev["id"], origin_row["id"], day)
                    yield (
                        "warning",
                        warning_event(
                            "no_route",
                            "no return from last city",
                            hub_id=frm["id"],
                            from_hub=frm["id"],
                            to_hub=to["id"],
                        ),
                    )
                    if alt is not None and alt["status"] == "ok" and not price_is_absent(alt["min_price"]):
                        row = alt
                        frm = prev
                        day = alt["date_probed"] or day
                    else:
                        continue
                else:
                    yield (
                        "warning",
                        warning_event(
                            "no_route",
                            "no_route",
                            hub_id=frm["id"],
                            from_hub=frm["id"],
                            to_hub=to["id"],
                        ),
                    )
                    continue

        dest_guard = guard_status(
            meta_from_hub(to),
            to["name"],
            to["expected_region"] or to["subject"],
        )
        if dest_guard != "ok" and to["id"] != origin_row["id"]:
            continue

        if row is None or row["status"] == "misresolved":
            if row is not None and row["status"] == "misresolved":
                yield (
                    "warning",
                    warning_event(
                        "misresolved",
                        "guard rejected destination",
                        hub_id=to["id"],
                        from_hub=frm["id"],
                        to_hub=to["id"],
                    ),
                )
            else:
                yield (
                    "warning",
                    warning_event(
                        "no_route",
                        "no_route",
                        hub_id=to["id"],
                        from_hub=frm["id"],
                        to_hub=to["id"],
                    ),
                )
            continue
        if row["status"] == "no_route" or price_is_absent(row["min_price"]):
            yield (
                "warning",
                warning_event(
                    "no_route",
                    "no_route",
                    hub_id=to["id"],
                    from_hub=frm["id"],
                    to_hub=to["id"],
                ),
            )
            continue

        cached = route_cache_payload(conn, frm["id"], to["id"], row["date_probed"])
        source = "cache"
        checkout_ref: Any = {}
        url = None
        if cached:
            url = checkout_url_from_obj(cached)
            ref = cached.get("checkout_ref")
            if isinstance(ref, dict):
                checkout_ref = ref
        price = int(row["min_price"])
        transport_total += price
        priced = True
        payload = {
            "from_hub": frm["id"],
            "to_hub": to["id"],
            "from_name": frm["resolved_name"] or frm["name"],
            "to_name": to["resolved_name"] or to["name"],
            "mode": pick_mode(row["modes"] or ""),
            "modes": row["modes"] or "",
            "price": price,
            "currency": CURRENCY,
            "duration_min": row["duration_min"],
            "date": row["date_probed"],
            "checkout_ref": checkout_ref,
            "source": source,
        }
        yield ("leg", payload)
        first_leg_sent = True
        if url:
            checkout_items.append(
                {
                    "kind": "leg",
                    "from_hub": frm["id"],
                    "to_hub": to["id"],
                    "checkout_url": url,
                }
            )
        if is_return:
            pass

    if not live_tutu_enabled():
        _ = later_window_starts(req["month"], window0)
    elif first_leg_sent:
        for extra in later_window_starts(req["month"], window0):
            _ = extra

    budget = req.get("budget_scope") or "transport"
    if budget == "all":
        for i, h in enumerate(visit):
            check_in = add_days(window0, i)
            check_out = add_days(check_in, 1)
            cached_h = hotel_cache_row(conn, h["id"], check_in, check_out, int(req["adults"]))
            if cached_h is None:
                yield (
                    "warning",
                    warning_event("no_hotel", "no_hotel", hub_id=h["id"]),
                )
                continue
            payload = json.loads(cached_h["payload_json"])
            amount = stay_total_from_hotel_payload(payload)
            if amount is None:
                yield (
                    "warning",
                    warning_event("no_hotel", "no_hotel", hub_id=h["id"]),
                )
                continue
            nights = nights_from_hotel_payload(payload, 1)
            lodging_total += amount
            priced = True
            city_meta = {}
            if isinstance(payload.get("meta"), dict):
                city_meta = payload["meta"].get("resolved_geo") or {}
            city = city_meta.get("name") if isinstance(city_meta, dict) else None
            hotel_event = {
                "hub_id": h["id"],
                "city": city or h["resolved_name"] or h["name"],
                "min_price": amount,
                "currency": CURRENCY,
                "nights": nights,
                "price_basis": "stay_total",
                "checkout_ref": payload.get("checkout_ref") or {},
                "source": "cache",
            }
            yield ("hotel", hotel_event)
            h_url = checkout_url_from_obj(payload)
            if h_url:
                checkout_items.append(
                    {
                        "kind": "hotel",
                        "from_hub": h["id"],
                        "to_hub": h["id"],
                        "checkout_url": h_url,
                    }
                )

    if priced:
        lodging = lodging_total if budget == "all" else 0
        total = transport_total + lodging
        yield (
            "breakdown",
            {
                "transport": transport_total,
                "lodging": lodging,
                "total": total,
                "currency": CURRENCY,
                "budget_scope": budget,
                "price_status": PRICE_STATUS,
            },
        )

    if checkout_items:
        yield ("checkout", {"items": checkout_items})

    _ = seen_return
    yield (
        "done",
        {
            "ok": True,
            "cluster_id": req["cluster_id"],
            "price_status": PRICE_STATUS,
        },
    )
