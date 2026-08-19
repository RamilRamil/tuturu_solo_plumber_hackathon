"""D2: directed legs between sellable hubs <=150 km that both have POI."""

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
    LEG_KM,
    PRODUCT_CONCURRENCY,
    SOFTFAIL_PATH,
    dump_json,
    haversine_km,
    log_mode_softfail,
    min_duration_min,
    now_iso,
    origin_hub_id,
    query_label,
    weekday_plus_weeks,
)

from lib.models import connect
from lib.tutu_mcp import TutuMcp, check_resolve, extract_meta, price_is_absent

_TLS = threading.local()


def _thread_mcp(db_path: Path) -> TutuMcp:
    mcp = getattr(_TLS, "mcp", None)
    if mcp is None:
        mcp = TutuMcp(db_path, timeout_s=CALL_TIMEOUT_S, max_concurrency=1)
        mcp.conn.execute("PRAGMA busy_timeout=60000")
        _TLS.mcp = mcp
    return mcp


def _load_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT h.id, h.name, h.subject, h.lat, h.lon, h.resolved_name,
               h.expected_region, h.probe_status
        FROM hub h
        WHERE h.probe_status = 'sellable'
          AND EXISTS (SELECT 1 FROM poi p WHERE p.hub_id = h.id)
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _pairs(hubs: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    origin = origin_hub_id()
    out: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for a in hubs:
        for b in hubs:
            if a["id"] == b["id"]:
                continue
            if a["id"] == origin or b["id"] == origin:
                continue
            d = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            if d <= LEG_KM:
                out.append((a, b))
    return out


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


def _probe_pair(
    db_path: Path,
    a: dict[str, Any],
    b: dict[str, Any],
    departure_date: str,
) -> dict[str, Any]:
    origin_q = query_label(a.get("resolved_name"), a["name"])
    expected = b.get("expected_region") or b["subject"]
    mcp = _thread_mcp(db_path)
    t0 = time.time()
    outcome = mcp.probe_destination(
        origin=origin_q,
        name=str(b["name"]),
        subject=str(b["subject"]),
        expected_region=str(expected),
        departure_date=departure_date,
        adults=1,
    )
    latency_ms = int((time.time() - t0) * 1000)
    if outcome.payload:
        meta = extract_meta(outcome.payload)
        if meta:
            check_resolve(meta, str(b["name"]), str(expected))
    min_price = outcome.min_price
    if min_price is not None and price_is_absent(min_price):
        min_price = None
    if outcome.status == "sellable":
        status = "ok"
    elif outcome.status == "misresolved":
        status = "misresolved"
    else:
        status = "no_route"
    return {
        "origin_hub": a["id"],
        "dest_hub": b["id"],
        "date_probed": departure_date,
        "modes": outcome.sellable_modes or "",
        "min_price": min_price,
        "duration_min": min_duration_min(outcome.payload),
        "latency_ms": latency_ms,
        "checked_at": now_iso(),
        "status": status,
        "payload": outcome.payload,
    }


def recompute_reachable(conn: sqlite3.Connection) -> None:
    origin = origin_hub_id()
    conn.execute("UPDATE hub SET reachable_from_any = 0")
    conn.execute(
        """
        UPDATE hub SET reachable_from_any = 1
        WHERE id = ?
           OR id IN (
             SELECT dest_hub FROM leg
             WHERE status = 'ok' AND origin_hub = ?
           )
        """,
        (origin, origin),
    )


def run_d2(
    db_path: Path,
    departure_date: str,
    workers: int = PRODUCT_CONCURRENCY,
) -> dict[str, Any]:
    if workers < 1 or workers > PRODUCT_CONCURRENCY:
        raise ValueError("workers must be 1..4")
    conn = connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    hubs = _load_candidates(conn)
    conn.close()
    conn = None
    pairs = _pairs(hubs)
    print("d2 candidates=%s directed_pairs=%s" % (len(hubs), len(pairs)), flush=True)
    softfail: list[dict[str, Any]] = []
    counts = {"ok": 0, "no_route": 0, "misresolved": 0}
    done = 0
    collected: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_probe_pair, db_path, a, b, departure_date) for a, b in pairs]
        for fut in as_completed(futs):
            row = fut.result()
            collected.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            done += 1
            if done % 10 == 0 or done == len(pairs):
                print(
                    "d2 progress %s/%s ok=%s no_route=%s misresolved=%s"
                    % (done, len(pairs), counts["ok"], counts["no_route"], counts["misresolved"]),
                    flush=True,
                )
    conn = connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    for row in collected:
        log_mode_softfail(row.get("payload"), softfail, "d2:%s->%s" % (row["origin_hub"], row["dest_hub"]))
        payload = row.pop("payload", None)
        _ = payload
        _upsert_leg(conn, row)
    recompute_reachable(conn)
    conn.commit()
    if softfail:
        dump_json(SOFTFAIL_PATH, softfail)
    summary = {
        "candidates": len(hubs),
        "pairs": len(pairs),
        "counts": counts,
        "departure_date": departure_date,
        "at": now_iso(),
    }
    conn.close()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DB_DEFAULT))
    parser.add_argument("--date", default="")
    parser.add_argument("--workers", type=int, default=PRODUCT_CONCURRENCY)
    args = parser.parse_args()
    departure = args.date or weekday_plus_weeks(3)
    summary = run_d2(Path(args.db), departure, workers=args.workers)
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
