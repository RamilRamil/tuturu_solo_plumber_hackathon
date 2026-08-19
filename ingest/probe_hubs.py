"""D1: probe sellable hubs. Uses lib.tutu_mcp (no MCP/guard copy)."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.common import (
    CALL_TIMEOUT_S,
    DB_DEFAULT,
    ORIGIN_NAME,
    ORIGIN_SUBJECT,
    PRODUCT_CONCURRENCY,
    REGRESSION_LABELS,
    SOFTFAIL_PATH,
    WAVE1_SUMMARY_PATH,
    dump_json,
    hub_id_of,
    log_mode_softfail,
    min_duration_min,
    now_iso,
    origin_hub_id,
    wave1_cities,
    weekday_plus_weeks,
)

from lib.models import connect
from lib.tutu_mcp import (
    SOURCE_HANDBOOK,
    TutuMcp,
    check_resolve,
    extract_meta,
    price_is_absent,
    resolve_expected_region,
)

_TLS = threading.local()


def _thread_mcp(db_path: Path) -> TutuMcp:
    mcp = getattr(_TLS, "mcp", None)
    if mcp is None:
        mcp = TutuMcp(db_path, timeout_s=CALL_TIMEOUT_S, max_concurrency=1)
        mcp.conn.execute("PRAGMA busy_timeout=60000")
        _TLS.mcp = mcp
    return mcp


def _geo_id_text(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def _upsert_hub(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO hub(
          id, name, subject, lat, lon, population, tutu_geo_id,
          resolved_name, resolved_region, probe_status, sellable_modes,
          reachable_from_any, expected_region, expected_region_source,
          min_price_from_moscow, latency_ms, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"],
            row["name"],
            row["subject"],
            row["lat"],
            row["lon"],
            row.get("population"),
            row.get("tutu_geo_id"),
            row.get("resolved_name"),
            row.get("resolved_region"),
            row["probe_status"],
            row.get("sellable_modes") or "",
            row.get("reachable_from_any") or 0,
            row.get("expected_region"),
            row.get("expected_region_source") or SOURCE_HANDBOOK,
            row.get("min_price_from_moscow"),
            row.get("latency_ms"),
            row.get("checked_at"),
        ),
    )


def _upsert_leg(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO leg(
          origin_hub, dest_hub, date_probed, modes, min_price,
          duration_min, latency_ms, checked_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["origin_hub"],
            row["dest_hub"],
            row["date_probed"],
            row.get("modes") or "",
            row.get("min_price"),
            row.get("duration_min"),
            row.get("latency_ms"),
            row.get("checked_at"),
            row["status"],
        ),
    )


def _origin_city(cities: list[dict[str, Any]]) -> dict[str, Any]:
    for city in cities:
        if city.get("name") == ORIGIN_NAME and city.get("subject") == ORIGIN_SUBJECT:
            return city
    raise RuntimeError("origin city missing from cities_ru.json")


def _insert_origin(conn: sqlite3.Connection, city: dict[str, Any], checked_at: str) -> None:
    expected, source = resolve_expected_region(True, str(city["subject"]), None)
    _upsert_hub(
        conn,
        {
            "id": origin_hub_id(),
            "name": ORIGIN_NAME,
            "subject": ORIGIN_SUBJECT,
            "lat": float(city["lat"]),
            "lon": float(city["lon"]),
            "population": int(city["population"]) if city.get("population") is not None else None,
            "tutu_geo_id": None,
            "resolved_name": ORIGIN_NAME,
            "resolved_region": ORIGIN_SUBJECT,
            "probe_status": "sellable",
            "sellable_modes": "avia,bus,etrain,railway",
            "reachable_from_any": 1,
            "expected_region": expected,
            "expected_region_source": source,
            "min_price_from_moscow": None,
            "latency_ms": None,
            "checked_at": checked_at,
        },
    )


def _probe_city(
    db_path: Path,
    city: dict[str, Any],
    origin: str,
    departure_date: str,
) -> dict[str, Any]:
    expected, source = resolve_expected_region(True, str(city["subject"]), None)
    if not expected:
        return {
            "city": city,
            "error": "missing_expected_region",
            "expected_region": None,
            "expected_region_source": source,
        }
    try:
        mcp = _thread_mcp(db_path)
        t0 = time.time()
        outcome = mcp.probe_destination(
            origin=origin,
            name=str(city["name"]),
            subject=str(city["subject"]),
            expected_region=expected,
            departure_date=departure_date,
            adults=1,
        )
        latency_ms = int((time.time() - t0) * 1000)
    except Exception as exc:
        return {
            "city": city,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "expected_region": expected,
            "expected_region_source": source,
        }
    # Guard already ran inside probe_destination; import is the seam, not a second copy.
    if outcome.payload:
        meta = extract_meta(outcome.payload)
        if meta:
            check_resolve(meta, str(city["name"]), expected)
    min_price = outcome.min_price
    if min_price is not None and price_is_absent(min_price):
        min_price = None
    return {
        "city": city,
        "error": None,
        "expected_region": expected,
        "expected_region_source": source,
        "status": outcome.status,
        "resolved_name": outcome.resolved_name,
        "resolved_region": outcome.resolved_region,
        "tutu_geo_id": _geo_id_text(outcome.tutu_geo_id),
        "sellable_modes": outcome.sellable_modes or "",
        "min_price": min_price,
        "payload": outcome.payload,
        "latency_ms": latency_ms,
        "query_used": outcome.query_used,
    }


def _leg_status(probe_status: str) -> str:
    if probe_status == "sellable":
        return "ok"
    if probe_status == "misresolved":
        return "misresolved"
    return "no_route"


def regression_missing(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name, resolved_name FROM hub").fetchall()
    labels = set()
    for row in rows:
        if row["name"]:
            labels.add(row["name"])
        if row["resolved_name"]:
            labels.add(row["resolved_name"])
    return [lab for lab in REGRESSION_LABELS if lab not in labels]


def run_wave1(
    db_path: Path,
    departure_date: str,
    workers: int = PRODUCT_CONCURRENCY,
) -> dict[str, Any]:
    if workers < 1 or workers > PRODUCT_CONCURRENCY:
        raise ValueError("workers must be 1..4")
    cities = wave1_cities()
    if len(cities) != 268:
        raise RuntimeError("wave 1 must be 268 cities with dM<=400, got %s" % len(cities))
    origin_row = _origin_city(cities)
    dests = [
        c
        for c in cities
        if not (c.get("name") == ORIGIN_NAME and c.get("subject") == ORIGIN_SUBJECT)
    ]
    conn = connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    checked_at = now_iso()
    _insert_origin(conn, origin_row, checked_at)
    conn.commit()
    conn.close()

    softfail: list[dict[str, Any]] = []
    errors: list[str] = []
    counts = {"sellable": 0, "not_sellable": 0, "misresolved": 0}
    done = 0
    origin_id = origin_hub_id()
    collected: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [
            pool.submit(_probe_city, db_path, city, ORIGIN_NAME, departure_date)
            for city in dests
        ]
        for fut in as_completed(futs):
            try:
                item = fut.result()
            except Exception as exc:
                errors.append(str(exc))
                print("d1 error %s" % exc, flush=True)
                continue
            collected.append(item)
            done += 1
            status = item.get("status") or "error"
            if item.get("error"):
                errors.append("%s: %s" % (hub_id_of(item["city"]), item["error"]))
            elif status in counts:
                counts[status] += 1
            if done % 10 == 0 or done == len(dests):
                print(
                    "d1 progress %s/%s sellable=%s not_sellable=%s misresolved=%s"
                    % (done, len(dests), counts["sellable"], counts["not_sellable"], counts["misresolved"]),
                    flush=True,
                )

    conn = connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    for item in collected:
        city = item["city"]
        hid = hub_id_of(city)
        if item.get("error") or not item.get("status"):
            continue
        status = item["status"]
        log_mode_softfail(item.get("payload"), softfail, "d1:" + hid)
        _upsert_hub(
            conn,
            {
                "id": hid,
                "name": city["name"],
                "subject": city["subject"],
                "lat": float(city["lat"]),
                "lon": float(city["lon"]),
                "population": int(city["population"]) if city.get("population") is not None else None,
                "tutu_geo_id": item.get("tutu_geo_id"),
                "resolved_name": item.get("resolved_name") or city["name"],
                "resolved_region": item.get("resolved_region"),
                "probe_status": status,
                "sellable_modes": item.get("sellable_modes") or "",
                "reachable_from_any": 1 if status == "sellable" else 0,
                "expected_region": item.get("expected_region"),
                "expected_region_source": item.get("expected_region_source"),
                "min_price_from_moscow": item.get("min_price"),
                "latency_ms": item.get("latency_ms"),
                "checked_at": checked_at,
            },
        )
        _upsert_leg(
            conn,
            {
                "origin_hub": origin_id,
                "dest_hub": hid,
                "date_probed": departure_date,
                "modes": item.get("sellable_modes") or "",
                "min_price": item.get("min_price"),
                "duration_min": min_duration_min(item.get("payload")),
                "latency_ms": item.get("latency_ms"),
                "checked_at": checked_at,
                "status": _leg_status(status),
            },
        )
    conn.commit()
    missing = regression_missing(conn)
    summary = {
        "wave": 1,
        "dM_max_km": 400,
        "cities": len(cities),
        "probed": done,
        "departure_date": departure_date,
        "counts": counts,
        "errors": errors,
        "regression_missing": missing,
        "regression_pass": not missing,
        "softfail_n": len(softfail),
        "db": str(db_path),
        "at": now_iso(),
    }
    dump_json(WAVE1_SUMMARY_PATH, summary)
    if softfail:
        dump_json(SOFTFAIL_PATH, softfail)
    conn.close()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DB_DEFAULT))
    parser.add_argument("--date", default="")
    parser.add_argument("--workers", type=int, default=PRODUCT_CONCURRENCY)
    args = parser.parse_args()
    departure = args.date or weekday_plus_weeks(3)
    print("d1 start date=%s workers=%s db=%s" % (departure, args.workers, args.db), flush=True)
    summary = run_wave1(Path(args.db), departure, workers=args.workers)
    print(summary, flush=True)
    if summary["regression_missing"]:
        print("REGRESSION FAIL missing=%s" % summary["regression_missing"], flush=True)
        return 2
    print("REGRESSION PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
