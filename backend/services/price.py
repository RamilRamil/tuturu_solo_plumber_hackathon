"""Phase-2 price planning. Guard and MCP come from lib.tutu_mcp (import only)."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from calendar import monthrange
from datetime import date, timedelta
from threading import Event
from typing import Any, Iterator, Optional

from lib.models import CLUSTER_ID_PREFIX, pax_sig
from lib.tutu_mcp import (
    CALL_TIMEOUT_S,
    MAX_CONCURRENCY,
    TutuMcp,
    check_resolve,
    extract_meta,
    load_aliases,
    normalize,
    price_is_absent,
    sellable_modes_from_meta,
    unwrap_tool_result,
)

PRICE_STATUS = "fixture-confirmed"
CURRENCY = "RUB"
FIRST_LEG_PAUSE_S = 3.0
EVENT_PAUSE_S = 1.0
DEFAULT_DB = "data/burger.db"
ASCII_ORIGIN_GEO = {"moscow": "fixture-mow", "moskva": "fixture-mow"}
_TRUTHY = ("1", "true", "yes", "on")


class UnknownCluster(Exception):
    """Illegal cluster_id or unknown hub (HTTP 404, not SSE warning)."""

    def __init__(self, cluster_id: str, reason: str = "unknown hub") -> None:
        self.cluster_id = cluster_id
        self.reason = reason
        super().__init__(reason)


def db_path() -> str:
    return os.environ.get("BURGER_DB") or DEFAULT_DB


def _env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in _TRUTHY


def live_tutu_enabled() -> bool:
    return _env_flag("BURGER_LIVE_TUTU")


def sc_price_accepted() -> bool:
    return _env_flag("BURGER_SC_PRICE_ACCEPTED")


def demo_pace_enabled() -> bool:
    return _env_flag("BURGER_PRICE_DEMO_PACE")


def overall_price_status() -> str:
    """Overall status is live only when BURGER_SC_PRICE_ACCEPTED is set."""
    return "live" if sc_price_accepted() else PRICE_STATUS


def open_mcp(path: Optional[str] = None) -> TutuMcp:
    return TutuMcp(
        path or db_path(),
        timeout_s=CALL_TIMEOUT_S,
        max_concurrency=MAX_CONCURRENCY,
    )


def parse_cluster_id_hubs(cluster_id: str) -> list[str]:
    """Parse G2 id: cluster_id = 'c:' + ',' .join(sorted(hub_id)). Do not mint a new format."""
    if not cluster_id.startswith(CLUSTER_ID_PREFIX):
        raise UnknownCluster(cluster_id, "illegal cluster_id")
    rest = cluster_id[len(CLUSTER_ID_PREFIX) :]
    if not rest:
        raise UnknownCluster(cluster_id, "illegal cluster_id")
    hub_ids = rest.split(",")
    if any(not hid for hid in hub_ids):
        raise UnknownCluster(cluster_id, "illegal cluster_id")
    return hub_ids


def resolve_cluster_hubs(conn: sqlite3.Connection, cluster_id: str) -> list[sqlite3.Row]:
    """Rebuild cluster membership from cluster_id + table hub. Table cluster is not required."""
    hub_ids = parse_cluster_id_hubs(cluster_id)
    hubs: list[sqlite3.Row] = []
    for hid in hub_ids:
        row = hub_row(conn, hid)
        if row is None:
            raise UnknownCluster(cluster_id, "unknown hub")
        hubs.append(row)
    return hubs


def load_cluster_row(conn: sqlite3.Connection, cluster_id: str) -> dict[str, Any]:
    hubs = resolve_cluster_hubs(conn, cluster_id)
    hub_ids = [h["id"] for h in hubs]
    title = hubs[0]["name"] if hubs else ""
    return {"id": cluster_id, "hub_ids": json.dumps(hub_ids), "title": title}


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
    adults: int,
    sig: str,
) -> Optional[dict[str, Any]]:
    row = conn.execute(
        """
        SELECT payload_json FROM route_cache
        WHERE origin_hub = ? AND dest_hub = ? AND date = ? AND adults = ? AND pax_sig = ?
        """,
        (origin_hub, dest_hub, day, adults, sig),
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
    sig: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM hotel_cache
        WHERE hub_id = ? AND check_in = ? AND check_out = ? AND adults = ? AND pax_sig = ?
        """,
        (hub_id, check_in, check_out, adults, sig),
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
    best = obj.get("best_offer")
    if isinstance(best, dict):
        nested = best.get("checkout_url")
        if isinstance(nested, str) and nested:
            return nested
    return None


def payload_offers(doc: Any) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    out: list[dict[str, Any]] = []
    for key in ("offers", "variants"):
        items = doc.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                out.append(item)
    return out


def offer_amount(off: dict[str, Any]) -> Any:
    p = off.get("price")
    if isinstance(p, dict):
        return p.get("amount")
    if p is not None:
        return p
    return off.get("min_price")


def pick_priced_offer(offers: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    best: Optional[dict[str, Any]] = None
    best_price: Optional[int] = None
    for off in offers:
        amt = offer_amount(off)
        if price_is_absent(amt):
            continue
        n = int(float(amt))
        if best_price is None or n < best_price:
            best = off
            best_price = n
    return best


def cache_leg_issue(row: Optional[sqlite3.Row]) -> Optional[str]:
    if row is None:
        return "no_route"
    status = row["status"] or ""
    if status == "misresolved":
        return "misresolved"
    if status == "no_route":
        return "no_route"
    if price_is_absent(row["min_price"]):
        return "no_price"
    return None


def query_city(row: sqlite3.Row) -> str:
    return (row["resolved_name"] or row["name"] or "").strip()


def quote_from_route_doc(doc: Any, day: str, source: str) -> Optional[dict[str, Any]]:
    parsed = unwrap_tool_result(doc) if isinstance(doc, dict) else doc
    if not isinstance(parsed, dict):
        return None
    offers = payload_offers(parsed)
    offer = pick_priced_offer(offers)
    if offer is None:
        return None
    price = int(float(offer_amount(offer)))
    if price_is_absent(price):
        return None
    meta = extract_meta(parsed) if parsed else {}
    modes = sellable_modes_from_meta(meta, offers)
    mode = str(offer.get("mode") or offer.get("transport") or "")
    if not modes:
        modes = mode
    duration = offer.get("duration_min")
    if duration is not None:
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = None
    ref = offer.get("checkout_ref")
    if not isinstance(ref, dict):
        ref = {}
    url = checkout_url_from_obj(offer) or checkout_url_from_obj(parsed)
    return {
        "price": price,
        "modes": modes,
        "mode": mode or pick_mode(modes),
        "duration_min": duration,
        "date": day,
        "checkout_ref": ref,
        "checkout_url": url,
        "source": source,
    }


def live_hop_quote(
    mcp: TutuMcp,
    frm: sqlite3.Row,
    to: sqlite3.Row,
    day: str,
    adults: int,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Search one directed hop. Returns (quote, issue_code). Never books."""
    try:
        outcome = mcp.probe_destination(
            origin=query_city(frm),
            name=to["name"],
            subject=to["subject"],
            expected_region=to["expected_region"] or to["subject"] or "",
            departure_date=day,
            adults=adults,
        )
    except Exception:
        return None, "cache_fallback"
    doc = outcome.payload if isinstance(outcome.payload, dict) else {}
    try:
        meta = extract_meta(doc) if doc else {}
        if not meta:
            meta = {
                "to": {
                    "name": outcome.resolved_name,
                    "region": outcome.resolved_region,
                    "geo_id": outcome.tutu_geo_id,
                }
            }
        ok, _reason = check_resolve(
            meta,
            to["name"],
            to["expected_region"] or to["subject"] or "",
        )
        if outcome.status == "misresolved" or not ok:
            return None, "misresolved"
        quote = quote_from_route_doc(doc, day, "live")
        if quote is None:
            offers = payload_offers(doc)
            if outcome.status == "not_sellable":
                return None, "not_sellable"
            if not offers:
                return None, "no_route"
            return None, "no_price"
        return quote, None
    except Exception:
        return None, "cache_fallback"


def exact_cache_quote(
    conn: sqlite3.Connection,
    frm: sqlite3.Row,
    to: sqlite3.Row,
    day: str,
    adults: int,
    sig: str,
) -> Optional[dict[str, Any]]:
    cached = route_cache_payload(conn, frm["id"], to["id"], day, adults, sig)
    if not cached:
        return None
    return quote_from_route_doc(cached, day, "cache")


def stale_leg_quote(
    conn: sqlite3.Connection,
    frm: sqlite3.Row,
    to: sqlite3.Row,
    day: str,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    row = directed_leg(conn, frm["id"], to["id"], day)
    issue = cache_leg_issue(row)
    if issue is not None or row is None:
        return None, issue or "no_route"
    price = int(row["min_price"])
    if price_is_absent(price):
        return None, "no_price"
    return (
        {
            "price": price,
            "modes": row["modes"] or "",
            "mode": pick_mode(row["modes"] or ""),
            "duration_min": row["duration_min"],
            "date": row["date_probed"],
            "checkout_ref": {},
            "checkout_url": None,
            "source": "cache",
            "stale": True,
        },
        None,
    )


def live_hotel_payload(
    mcp: TutuMcp,
    hub: sqlite3.Row,
    check_in: str,
    check_out: str,
    adults: int,
    children_ages: Optional[list[int]] = None,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    args: dict[str, Any] = {
        "city_name": query_city(hub),
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
    }
    if children_ages:
        args["children_ages"] = list(children_ages)
    try:
        raw = mcp.call_tool("search_hotels", args)
    except Exception:
        return None, "cache_fallback"
    doc = unwrap_tool_result(raw)
    if not isinstance(doc, dict):
        return None, "no_hotel"
    meta = extract_meta(doc)
    geo = {}
    if isinstance(doc.get("meta"), dict):
        maybe = doc["meta"].get("resolved_geo")
        if isinstance(maybe, dict):
            geo = maybe
    if geo:
        meta = {"to": {"name": geo.get("name") or "", "region": geo.get("region") or ""}}
    if meta:
        ok, _reason = check_resolve(
            meta,
            hub["name"],
            hub["expected_region"] or hub["subject"] or "",
        )
        if not ok:
            return None, "misresolved"
    amount = stay_total_from_hotel_payload(doc)
    if amount is None:
        return None, "no_hotel"
    return doc, None


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


WARN_MESSAGES = {
    "misresolved": "guard rejected destination",
    "not_sellable": "not_sellable",
    "no_route": "no_route",
    "no_price": "no_price",
    "no_hotel": "no_hotel",
    "cache_fallback": "cache_fallback",
    "stale_leg": "stale_leg",
    "child_fare_unverified": "search_multitransport is adults-only",
}


def warning_event(
    code: str,
    message: str,
    hub_id: Optional[str] = None,
    from_hub: str = "",
    to_hub: str = "",
    recovered: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "hub_id": hub_id,
        "leg": {"from_hub": from_hub, "to_hub": to_hub},
    }
    if recovered:
        payload["recovered"] = True
    return payload


def warn_code(
    code: str,
    hub_id: Optional[str],
    from_hub: str,
    to_hub: str,
    recovered: bool = False,
) -> dict[str, Any]:
    return warning_event(
        code,
        WARN_MESSAGES.get(code, code),
        hub_id=hub_id,
        from_hub=from_hub,
        to_hub=to_hub,
        recovered=recovered,
    )


def quote_directed_hop(
    mcp: TutuMcp,
    frm: sqlite3.Row,
    to: sqlite3.Row,
    day: str,
    adults: int,
    live_on: bool,
    sig: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[str], bool]:
    live_issue: Optional[str] = None
    if live_on:
        quote, live_issue = live_hop_quote(mcp, frm, to, day, adults)
        if quote is not None:
            return quote, None, False
    exact = exact_cache_quote(mcp.conn, frm, to, day, adults, sig)
    if exact is not None:
        if live_on and live_issue is not None:
            return exact, "cache_fallback", True
        return exact, None, False
    quote, stale_issue = stale_leg_quote(mcp.conn, frm, to, day)
    if quote is not None:
        if live_on and live_issue is not None:
            return quote, "cache_fallback", True
        return quote, "stale_leg", True
    issue = stale_issue or live_issue or "no_route"
    if issue == "cache_fallback":
        issue = stale_issue or "no_route"
    return None, issue, False


def _cancelled(cancel: Optional[Event]) -> bool:
    return cancel is not None and cancel.is_set()


def iter_price_events(
    req: dict[str, Any],
    mcp: TutuMcp,
    cancel: Optional[Event] = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (event_name, payload). Caller must not block the event loop."""
    conn = mcp.conn
    cluster_hubs = resolve_cluster_hubs(conn, req["cluster_id"])

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
        elif (h["probe_status"] or "") == "not_sellable":
            hub_warnings.append(
                warning_event(
                    "not_sellable",
                    WARN_MESSAGES.get("not_sellable", "not_sellable"),
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

    status = overall_price_status()
    if origin_row is None or origin_guard != "ok":
        yield (
            "done",
            {
                "ok": True,
                "cluster_id": req["cluster_id"],
                "price_status": status,
            },
        )
        return

    children_ages = [int(a) for a in (req.get("children_ages") or [])]
    sig = pax_sig(children_ages)
    if children_ages:
        yield (
            "warning",
            warn_code("child_fare_unverified", None, "", ""),
        )

    window0 = first_window_start(req["month"])
    visit = order_visit(conn, origin_row, cluster_hubs, window0)
    return_date = add_days(window0, max(0, int(req["days"]) - 1))
    priced = False
    transport_total = 0
    lodging_total = 0
    checkout_items: list[dict[str, Any]] = []
    first_leg_sent = False
    live_on = live_tutu_enabled()
    adults = int(req["adults"])
    hops: list[tuple[sqlite3.Row, sqlite3.Row, str]] = []
    current = origin_row
    for dest in visit:
        hops.append((current, dest, window0))
        current = dest
    hops.append((current, origin_row, return_date))
    prev_city = visit[-2] if len(visit) >= 2 else None

    def emit_leg(frm_h: sqlite3.Row, to_h: sqlite3.Row, quote: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
        nonlocal priced, transport_total, first_leg_sent
        price = int(quote["price"])
        if price_is_absent(price):
            yield (
                "warning",
                warn_code("no_price", to_h["id"], frm_h["id"], to_h["id"]),
            )
            return
        transport_total += price
        priced = True
        payload: dict[str, Any] = {
            "from_hub": frm_h["id"],
            "to_hub": to_h["id"],
            "from_name": frm_h["resolved_name"] or frm_h["name"],
            "to_name": to_h["resolved_name"] or to_h["name"],
            "mode": quote.get("mode") or pick_mode(quote.get("modes") or ""),
            "modes": quote.get("modes") or "",
            "price": price,
            "currency": CURRENCY,
            "duration_min": quote.get("duration_min"),
            "date": quote.get("date"),
            "checkout_ref": quote.get("checkout_ref") or {},
            "source": quote.get("source") or "cache",
        }
        if quote.get("stale"):
            payload["stale"] = True
        yield ("leg", payload)
        first_leg_sent = True
        url = quote.get("checkout_url")
        if isinstance(url, str) and url:
            checkout_items.append(
                {
                    "kind": "leg",
                    "from_hub": frm_h["id"],
                    "to_hub": to_h["id"],
                    "checkout_url": url,
                }
            )

    for frm, to, day in hops:
        if _cancelled(cancel):
            return
        is_return = to["id"] == origin_row["id"]
        dest_guard = guard_status(
            meta_from_hub(to),
            to["name"],
            to["expected_region"] or to["subject"],
        )
        if dest_guard != "ok" and to["id"] != origin_row["id"]:
            continue

        quote, issue, _used_fb = quote_directed_hop(
            mcp, frm, to, day, adults, live_on, sig
        )
        if is_return and quote is None and prev_city is not None and prev_city["id"] != frm["id"]:
            fb_quote, fb_issue, _fb_used = quote_directed_hop(
                mcp, prev_city, origin_row, day, adults, live_on, sig
            )
            if fb_quote is not None:
                yield (
                    "warning",
                    warn_code(
                        "no_route",
                        frm["id"],
                        frm["id"],
                        to["id"],
                        recovered=True,
                    ),
                )
                if fb_issue in ("cache_fallback", "stale_leg"):
                    yield (
                        "warning",
                        warn_code(fb_issue, to["id"], prev_city["id"], to["id"]),
                    )
                frm = prev_city
                quote = fb_quote
                issue = fb_issue
            else:
                yield (
                    "warning",
                    warn_code(issue or "no_route", frm["id"], frm["id"], to["id"]),
                )
                yield (
                    "warning",
                    warn_code(fb_issue or "no_route", to["id"], prev_city["id"], to["id"]),
                )
                continue
        elif quote is None:
            yield (
                "warning",
                warn_code(issue or "no_route", to["id"], frm["id"], to["id"]),
            )
            continue
        if issue in ("cache_fallback", "stale_leg"):
            yield (
                "warning",
                warn_code(issue, to["id"], frm["id"], to["id"]),
            )

        yield from emit_leg(frm, to, quote)

    if not live_on:
        _ = later_window_starts(req["month"], window0)
    elif first_leg_sent:
        for extra in later_window_starts(req["month"], window0):
            _ = extra

    budget = req.get("budget_scope") or "transport"
    if budget == "all":
        for i, h in enumerate(visit):
            if _cancelled(cancel):
                return
            check_in = add_days(window0, i)
            check_out = add_days(check_in, 1)
            hotel_doc: Optional[dict[str, Any]] = None
            hotel_source = "cache"
            live_hotel_issue: Optional[str] = None
            if live_on:
                hotel_doc, live_hotel_issue = live_hotel_payload(
                    mcp, h, check_in, check_out, adults, children_ages
                )
                if hotel_doc is not None:
                    hotel_source = "live"
            if hotel_doc is None:
                cached_h = hotel_cache_row(
                    conn, h["id"], check_in, check_out, adults, sig
                )
                if cached_h is None:
                    yield (
                        "warning",
                        warn_code(live_hotel_issue or "no_hotel", h["id"], "", ""),
                    )
                    continue
                hotel_doc = json.loads(cached_h["payload_json"])
                hotel_source = "cache"
                if live_on and live_hotel_issue is not None:
                    yield (
                        "warning",
                        warn_code("cache_fallback", h["id"], "", ""),
                    )
            amount = stay_total_from_hotel_payload(hotel_doc)
            if amount is None:
                yield (
                    "warning",
                    warn_code("no_hotel", h["id"], "", ""),
                )
                continue
            nights = nights_from_hotel_payload(hotel_doc, 1)
            lodging_total += amount
            priced = True
            city_meta = {}
            if isinstance(hotel_doc.get("meta"), dict):
                city_meta = hotel_doc["meta"].get("resolved_geo") or {}
            city = city_meta.get("name") if isinstance(city_meta, dict) else None
            href = hotel_doc.get("checkout_ref") or {}
            if not isinstance(href, dict):
                href = {}
            hotel_event = {
                "hub_id": h["id"],
                "city": city or h["resolved_name"] or h["name"],
                "min_price": amount,
                "currency": CURRENCY,
                "nights": nights,
                "price_basis": "stay_total",
                "checkout_ref": href,
                "source": hotel_source,
            }
            yield ("hotel", hotel_event)
            h_url = checkout_url_from_obj(hotel_doc)
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
                "price_status": status,
            },
        )

    if checkout_items:
        yield ("checkout", {"items": checkout_items})

    yield (
        "done",
        {
            "ok": True,
            "cluster_id": req["cluster_id"],
            "price_status": status,
        },
    )
