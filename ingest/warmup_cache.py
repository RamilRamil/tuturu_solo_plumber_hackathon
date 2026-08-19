"""D5: warmup route_cache and hotel_cache for etalon v2 windows (Oct 2026)."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.common import (
    CALL_TIMEOUT_S,
    DB_DEFAULT,
    PRODUCT_CONCURRENCY,
    dump_json,
    now_iso,
    query_label,
)

from lib.models import connect, make_hub_id, pax_sig
from lib.tutu_mcp import (
    TutuMcp,
    extract_meta,
    price_is_absent,
    sellable_modes_from_meta,
    unwrap_tool_result,
)

WINDOWS = (
    date(2026, 10, 2),
    date(2026, 10, 9),
    date(2026, 10, 16),
    date(2026, 10, 23),
)
ADULTS = (1, 2)
PAX_SIG = pax_sig([])
RETRY_TRIES = 3
RETRY_SLEEP_S = 2.0
SUMMARY_PATH = _ROOT / "data" / "d5_uglich_summary.json"

MOSCOW = (
    "\u041c\u043e\u0441\u043a\u0432\u0430",
    "\u041c\u043e\u0441\u043a\u0432\u0430",
)
YAROSLAVL = (
    "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u043b\u044c",
    "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
)
UGLICH = (
    "\u0423\u0433\u043b\u0438\u0447",
    "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
)

_TLS = threading.local()


def live_db_default() -> Path:
    """Main live burger.db, never the data-worktree copy."""
    parts = _ROOT.parts
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        return Path(*parts[:idx]) / "data" / "burger.db"
    return DB_DEFAULT


def _hub_row(conn: Any, name: str, subject: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, name, subject, resolved_name FROM hub WHERE id = ?",
        (make_hub_id(name, subject),),
    ).fetchone()
    return dict(row) if row else None


def _thread_mcp(db_path: Path) -> TutuMcp:
    mcp = getattr(_TLS, "mcp", None)
    if mcp is None:
        mcp = TutuMcp(db_path, timeout_s=CALL_TIMEOUT_S, max_concurrency=1)
        mcp.conn.execute("PRAGMA busy_timeout=60000")
        _TLS.mcp = mcp
    return mcp


def _call_with_retry(mcp: TutuMcp, tool: str, args: dict[str, Any]) -> Any:
    last: Exception | None = None
    for attempt in range(RETRY_TRIES):
        try:
            return mcp.call_tool(tool, args)
        except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
            last = exc
            time.sleep(RETRY_SLEEP_S * float(attempt + 1))
    if last is not None:
        raise last
    raise RuntimeError("retry exhausted")


def _store_doc(payload: Any) -> dict[str, Any]:
    doc = unwrap_tool_result(payload)
    if isinstance(doc, dict):
        return doc
    return {"raw": payload}


def _offer_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in ("offers", "variants"):
        items = doc.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                out.append(item)
    return out


def _offer_amount(off: dict[str, Any]) -> Any:
    p = off.get("price")
    if isinstance(p, dict):
        return p.get("amount")
    if p is not None:
        return p
    return off.get("min_price")


def _min_price_from_doc(doc: dict[str, Any]) -> int | None:
    prices: list[int] = []
    for off in _offer_rows(doc):
        amt = _offer_amount(off)
        if price_is_absent(amt):
            continue
        prices.append(int(float(amt)))
    meta = extract_meta(doc)
    summary = meta.get("modes_summary") or {}
    if isinstance(summary, dict):
        for info in summary.values():
            if not isinstance(info, dict):
                continue
            amt = info.get("min_price")
            if price_is_absent(amt):
                continue
            prices.append(int(float(amt)))
    return min(prices) if prices else None


def _route_empty(doc: dict[str, Any]) -> bool:
    meta = extract_meta(doc)
    modes = sellable_modes_from_meta(meta, _offer_rows(doc))
    if modes:
        return False
    return _min_price_from_doc(doc) is None


def _hotel_empty(doc: dict[str, Any]) -> bool:
    hotels = doc.get("hotels")
    if not isinstance(hotels, list) or not hotels:
        return True
    offer = hotels[0]
    if not isinstance(offer, dict):
        return True
    amount = offer.get("min_price")
    stay = offer.get("stay")
    if amount is None and isinstance(stay, dict):
        amount = stay.get("stay_total")
    return price_is_absent(amount)


def _stay_total(payload: Any) -> None:
    # Hotel price is stay_total. Never multiply by nights here.
    _ = payload
    _ = price_is_absent


def _route_exists(
    conn: Any, origin_hub: str, dest_hub: str, day: str, adults: int, sig: str
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM route_cache
        WHERE origin_hub = ? AND dest_hub = ? AND date = ? AND adults = ? AND pax_sig = ?
        """,
        (origin_hub, dest_hub, day, adults, sig),
    ).fetchone()
    return row is not None


def _hotel_exists(
    conn: Any,
    hub_id: str,
    check_in: str,
    check_out: str,
    adults: int,
    sig: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM hotel_cache
        WHERE hub_id = ? AND check_in = ? AND check_out = ? AND adults = ? AND pax_sig = ?
        """,
        (hub_id, check_in, check_out, adults, sig),
    ).fetchone()
    return row is not None


def _jobs(hubs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    moscow = hubs["moscow"]
    yar = hubs["yaroslavl"]
    ugl = hubs["uglich"]
    jobs: list[dict[str, Any]] = []
    for start in WINDOWS:
        outbound = start.isoformat()
        ret = (start + timedelta(days=2)).isoformat()
        check_in = outbound
        check_out = (start + timedelta(days=1)).isoformat()
        for adults in ADULTS:
            jobs.append(
                {
                    "kind": "route",
                    "origin": moscow,
                    "dest": yar,
                    "day": outbound,
                    "adults": adults,
                    "skip_empty": False,
                    "label": "moscow_yaroslavl",
                }
            )
            jobs.append(
                {
                    "kind": "route",
                    "origin": yar,
                    "dest": moscow,
                    "day": ret,
                    "adults": adults,
                    "skip_empty": False,
                    "label": "yaroslavl_moscow",
                }
            )
            jobs.append(
                {
                    "kind": "hotel",
                    "hub": yar,
                    "check_in": check_in,
                    "check_out": check_out,
                    "adults": adults,
                    "skip_empty": False,
                    "label": "hotel_yaroslavl",
                }
            )
            jobs.append(
                {
                    "kind": "hotel",
                    "hub": ugl,
                    "check_in": check_in,
                    "check_out": check_out,
                    "adults": adults,
                    "skip_empty": False,
                    "label": "hotel_uglich",
                }
            )
            jobs.append(
                {
                    "kind": "route",
                    "origin": moscow,
                    "dest": ugl,
                    "day": outbound,
                    "adults": adults,
                    "skip_empty": True,
                    "label": "moscow_uglich",
                }
            )
            jobs.append(
                {
                    "kind": "route",
                    "origin": ugl,
                    "dest": moscow,
                    "day": ret,
                    "adults": adults,
                    "skip_empty": True,
                    "label": "uglich_moscow",
                }
            )
    return jobs


def _run_job(db_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    mcp = _thread_mcp(db_path)
    kind = job["kind"]
    adults = int(job["adults"])
    try:
        if kind == "route":
            origin = job["origin"]
            dest = job["dest"]
            origin_q = query_label(origin.get("resolved_name"), origin["name"])
            dest_q = query_label(dest.get("resolved_name"), dest["name"])
            raw = _call_with_retry(
                mcp,
                "search_multitransport",
                {
                    "origin": origin_q,
                    "destination": dest_q,
                    "departure_date": job["day"],
                    "adults": adults,
                    "page_size": 1,
                },
            )
            doc = _store_doc(raw)
            empty = _route_empty(doc)
            return {
                "ok": True,
                "kind": kind,
                "label": job["label"],
                "skip_empty": job["skip_empty"],
                "empty": empty,
                "doc": doc,
                "min_price": _min_price_from_doc(doc),
                "origin_id": origin["id"],
                "dest_id": dest["id"],
                "day": job["day"],
                "adults": adults,
            }
        hub = job["hub"]
        city_q = query_label(hub.get("resolved_name"), hub["name"])
        raw = _call_with_retry(
            mcp,
            "search_hotels",
            {
                "city_name": city_q,
                "check_in": job["check_in"],
                "check_out": job["check_out"],
                "adults": adults,
            },
        )
        _stay_total(raw)
        doc = _store_doc(raw)
        empty = _hotel_empty(doc)
        return {
            "ok": True,
            "kind": kind,
            "label": job["label"],
            "skip_empty": job["skip_empty"],
            "empty": empty,
            "doc": doc,
            "hub_id": hub["id"],
            "check_in": job["check_in"],
            "check_out": job["check_out"],
            "adults": adults,
        }
    except Exception as exc:
        return {
            "ok": False,
            "kind": kind,
            "label": job["label"],
            "error": type(exc).__name__ + ": " + str(exc),
            "adults": adults,
        }


def _fill_ok_leg_min_price(
    conn: Any, origin_hub: str, dest_hub: str, min_price: int
) -> int:
    cur = conn.execute(
        """
        UPDATE leg
        SET min_price = ?
        WHERE origin_hub = ? AND dest_hub = ?
          AND status = 'ok' AND min_price IS NULL
        """,
        (min_price, origin_hub, dest_hub),
    )
    return int(cur.rowcount or 0)


def run_d5(db_path: Path, workers: int = PRODUCT_CONCURRENCY) -> dict[str, Any]:
    if workers < 1 or workers > PRODUCT_CONCURRENCY:
        raise ValueError("workers must be 1..4")
    fetched_at = now_iso()
    conn = connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    moscow = _hub_row(conn, *MOSCOW)
    yar = _hub_row(conn, *YAROSLAVL)
    ugl = _hub_row(conn, *UGLICH)
    missing = [
        name
        for name, row in (
            ("moscow", moscow),
            ("yaroslavl", yar),
            ("uglich", ugl),
        )
        if row is None
    ]
    if missing:
        conn.close()
        return {
            "attempted": 0,
            "succeeded": 0,
            "unique_rows": 0,
            "overwritten": 0,
            "errors": 0,
            "empty_skipped": 0,
            "missing_hubs": missing,
            "db": str(db_path),
            "at": fetched_at,
        }
    hubs = {"moscow": moscow, "yaroslavl": yar, "uglich": ugl}
    jobs = _jobs(hubs)
    conn.close()
    conn = None

    attempted = len(jobs)
    succeeded = 0
    overwritten = 0
    errors = 0
    empty_skipped = 0
    unique_keys: set[tuple[Any, ...]] = set()
    route_n = 0
    hotel_n = 0
    error_rows: list[dict[str, Any]] = []
    empty_labels: dict[str, int] = {}
    min_price_filled = 0
    by_label: dict[str, int] = {}

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_run_job, db_path, job) for job in jobs]
        done = 0
        for fut in as_completed(futs):
            row = fut.result()
            results.append(row)
            done += 1
            if done % 8 == 0 or done == len(jobs):
                print(
                    "d5 progress %s/%s" % (done, len(jobs)),
                    flush=True,
                )

    conn = connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    for row in results:
        label = str(row.get("label") or "")
        by_label[label] = by_label.get(label, 0) + 1
        if not row.get("ok"):
            errors += 1
            error_rows.append(
                {"label": label, "error": row.get("error"), "adults": row.get("adults")}
            )
            continue
        succeeded += 1
        skip_insert = bool(row.get("empty") and row.get("skip_empty"))
        if skip_insert:
            empty_skipped += 1
            empty_labels[label] = empty_labels.get(label, 0) + 1
            continue
        if row.get("empty"):
            empty_labels[label] = empty_labels.get(label, 0) + 1
        doc = row["doc"]
        adults = int(row["adults"])
        if row["kind"] == "route":
            origin_id = row["origin_id"]
            dest_id = row["dest_id"]
            day = row["day"]
            key = ("route", origin_id, dest_id, day, adults, PAX_SIG)
            if _route_exists(conn, origin_id, dest_id, day, adults, PAX_SIG):
                overwritten += 1
            conn.execute(
                """
                INSERT OR REPLACE INTO route_cache(
                  origin_hub, dest_hub, date, adults, pax_sig,
                  payload_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    origin_id,
                    dest_id,
                    day,
                    adults,
                    PAX_SIG,
                    json.dumps(doc, ensure_ascii=True),
                    fetched_at,
                ),
            )
            unique_keys.add(key)
            route_n += 1
            price = row.get("min_price")
            if isinstance(price, int) and price > 0:
                min_price_filled += _fill_ok_leg_min_price(
                    conn, origin_id, dest_id, price
                )
        else:
            hub_id = row["hub_id"]
            check_in = row["check_in"]
            check_out = row["check_out"]
            key = ("hotel", hub_id, check_in, check_out, adults, PAX_SIG)
            if _hotel_exists(conn, hub_id, check_in, check_out, adults, PAX_SIG):
                overwritten += 1
            conn.execute(
                """
                INSERT OR REPLACE INTO hotel_cache(
                  hub_id, check_in, check_out, adults, pax_sig,
                  payload_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hub_id,
                    check_in,
                    check_out,
                    adults,
                    PAX_SIG,
                    json.dumps(doc, ensure_ascii=True),
                    fetched_at,
                ),
            )
            unique_keys.add(key)
            hotel_n += 1
    conn.commit()
    route_total = conn.execute("SELECT COUNT(*) AS n FROM route_cache").fetchone()["n"]
    hotel_total = conn.execute("SELECT COUNT(*) AS n FROM hotel_cache").fetchone()["n"]
    conn.close()
    summary = {
        "attempted": attempted,
        "succeeded": succeeded,
        "unique_rows": len(unique_keys),
        "overwritten": overwritten,
        "errors": errors,
        "empty_skipped": empty_skipped,
        "empty_labels": empty_labels,
        "route_cache_written": route_n,
        "hotel_cache_written": hotel_n,
        "route_cache": route_total,
        "hotel_cache": hotel_total,
        "min_price_filled": min_price_filled,
        "by_label": by_label,
        "error_rows": error_rows,
        "windows": [d.isoformat() for d in WINDOWS],
        "adults": list(ADULTS),
        "pax_sig": PAX_SIG,
        "workers": workers,
        "db": str(db_path),
        "backup_same_as_moscow_yaroslavl": True,
        "note": (
            "etalon v2: Moscow<->Yaroslavl tickets + Yaroslavl/Uglich hotels; "
            "Moscow<->Uglich expected empty (no invent); skip insert if empty"
        ),
        "at": fetched_at,
    }
    dump_json(SUMMARY_PATH, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(live_db_default()))
    parser.add_argument("--workers", type=int, default=PRODUCT_CONCURRENCY)
    args = parser.parse_args()
    db_path = Path(args.db).resolve()
    db_s = str(db_path)
    if "/.worktrees/data/" in db_s:
        print("refusing data-worktree burger.db", flush=True)
        return 2
    summary = run_d5(db_path, workers=args.workers)
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
