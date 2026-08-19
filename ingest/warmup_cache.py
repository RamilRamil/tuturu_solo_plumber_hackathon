"""D5: warmup route_cache and hotel_cache for etalon windows (Oct 2026)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingest.common import CALL_TIMEOUT_S, DB_DEFAULT, now_iso, query_label

from lib.models import make_hub_id, pax_sig
from lib.tutu_mcp import TutuMcp, price_is_absent

WINDOWS = (
    date(2026, 10, 2),
    date(2026, 10, 9),
    date(2026, 10, 16),
    date(2026, 10, 23),
)
ADULTS = (1, 2)
PAX_SIG = pax_sig([])

ETALONS = (
    (
        ("\u041c\u043e\u0441\u043a\u0432\u0430", "\u041c\u043e\u0441\u043a\u0432\u0430"),
        ("\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u043b\u044c", "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
        ("\u0420\u043e\u0441\u0442\u043e\u0432", "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
    ),
    (
        ("\u041c\u043e\u0441\u043a\u0432\u0430", "\u041c\u043e\u0441\u043a\u0432\u0430"),
        ("\u0420\u044f\u0437\u0430\u043d\u044c", "\u0420\u044f\u0437\u0430\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
        ("\u041a\u043e\u043b\u043e\u043c\u043d\u0430", "\u041c\u043e\u0441\u043a\u043e\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
    ),
    (
        ("\u041c\u043e\u0441\u043a\u0432\u0430", "\u041c\u043e\u0441\u043a\u0432\u0430"),
        ("\u0422\u0443\u043b\u0430", "\u0422\u0443\u043b\u044c\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
        ("\u041a\u0430\u043b\u0443\u0433\u0430", "\u041a\u0430\u043b\u0443\u0436\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
    ),
    (
        ("\u041c\u043e\u0441\u043a\u0432\u0430", "\u041c\u043e\u0441\u043a\u0432\u0430"),
        ("\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440", "\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
        ("\u0418\u0432\u0430\u043d\u043e\u0432\u043e", "\u0418\u0432\u0430\u043d\u043e\u0432\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c"),
    ),
)


def _hub_row(mcp: TutuMcp, name: str, subject: str) -> dict[str, Any] | None:
    row = mcp.conn.execute(
        "SELECT id, name, subject, resolved_name FROM hub WHERE id = ?",
        (make_hub_id(name, subject),),
    ).fetchone()
    return dict(row) if row else None


def _stay_total(payload: Any) -> None:
    # Hotel price is stay_total. Never multiply by nights here.
    _ = payload
    _ = price_is_absent


def _route_exists(
    mcp: TutuMcp, origin_hub: str, dest_hub: str, day: str, adults: int, sig: str
) -> bool:
    row = mcp.conn.execute(
        """
        SELECT 1 FROM route_cache
        WHERE origin_hub = ? AND dest_hub = ? AND date = ? AND adults = ? AND pax_sig = ?
        """,
        (origin_hub, dest_hub, day, adults, sig),
    ).fetchone()
    return row is not None


def _hotel_exists(
    mcp: TutuMcp,
    hub_id: str,
    check_in: str,
    check_out: str,
    adults: int,
    sig: str,
) -> bool:
    row = mcp.conn.execute(
        """
        SELECT 1 FROM hotel_cache
        WHERE hub_id = ? AND check_in = ? AND check_out = ? AND adults = ? AND pax_sig = ?
        """,
        (hub_id, check_in, check_out, adults, sig),
    ).fetchone()
    return row is not None


def run_d5(db_path: Path) -> dict[str, Any]:
    mcp = TutuMcp(db_path, timeout_s=CALL_TIMEOUT_S, max_concurrency=4)
    fetched_at = now_iso()
    attempted = 0
    succeeded = 0
    overwritten = 0
    errors = 0
    unique_keys: set[tuple[Any, ...]] = set()
    route_n = 0
    hotel_n = 0
    skipped = 0
    for etalon in ETALONS:
        hubs = []
        for name, subject in etalon:
            row = _hub_row(mcp, name, subject)
            if row is None:
                skipped += 1
                hubs = []
                break
            hubs.append(row)
        if len(hubs) != 3:
            continue
        chain = [hubs[0], hubs[1], hubs[2], hubs[0]]
        for start in WINDOWS:
            outbound = start.isoformat()
            ret = (start + timedelta(days=2)).isoformat()
            for adults in ADULTS:
                for i in range(3):
                    a = chain[i]
                    b = chain[i + 1]
                    dep = outbound if i < 2 else ret
                    origin_q = query_label(a.get("resolved_name"), a["name"])
                    dest_q = query_label(b.get("resolved_name"), b["name"])
                    attempted += 1
                    try:
                        payload = mcp.call_tool(
                            "search_multitransport",
                            {
                                "origin": origin_q,
                                "destination": dest_q,
                                "departure_date": dep,
                                "adults": adults,
                                "page_size": 1,
                            },
                        )
                        key = (a["id"], b["id"], dep, adults, PAX_SIG)
                        if _route_exists(mcp, a["id"], b["id"], dep, adults, PAX_SIG):
                            overwritten += 1
                        mcp.conn.execute(
                            """
                            INSERT OR REPLACE INTO route_cache(
                              origin_hub, dest_hub, date, adults, pax_sig,
                              payload_json, fetched_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                a["id"],
                                b["id"],
                                dep,
                                adults,
                                PAX_SIG,
                                json.dumps(payload, ensure_ascii=True),
                                fetched_at,
                            ),
                        )
                        unique_keys.add(("route",) + key)
                        succeeded += 1
                        route_n += 1
                    except Exception:
                        errors += 1
                for stay_hub, check_in, check_out in (
                    (hubs[1], outbound, (start + timedelta(days=1)).isoformat()),
                    (hubs[2], (start + timedelta(days=1)).isoformat(), ret),
                ):
                    city_q = query_label(stay_hub.get("resolved_name"), stay_hub["name"])
                    attempted += 1
                    try:
                        payload = mcp.call_tool(
                            "search_hotels",
                            {
                                "city_name": city_q,
                                "check_in": check_in,
                                "check_out": check_out,
                                "adults": adults,
                            },
                        )
                        _stay_total(payload)
                        key = (stay_hub["id"], check_in, check_out, adults, PAX_SIG)
                        if _hotel_exists(
                            mcp, stay_hub["id"], check_in, check_out, adults, PAX_SIG
                        ):
                            overwritten += 1
                        mcp.conn.execute(
                            """
                            INSERT OR REPLACE INTO hotel_cache(
                              hub_id, check_in, check_out, adults, pax_sig,
                              payload_json, fetched_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                stay_hub["id"],
                                check_in,
                                check_out,
                                adults,
                                PAX_SIG,
                                json.dumps(payload, ensure_ascii=True),
                                fetched_at,
                            ),
                        )
                        unique_keys.add(("hotel",) + key)
                        succeeded += 1
                        hotel_n += 1
                    except Exception:
                        errors += 1
                mcp.conn.commit()
    mcp.close()
    return {
        "attempted": attempted,
        "succeeded": succeeded,
        "unique_rows": len(unique_keys),
        "overwritten": overwritten,
        "errors": errors,
        "route_cache": route_n,
        "hotel_cache": hotel_n,
        "skipped_etalons": skipped,
        "at": fetched_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DB_DEFAULT))
    args = parser.parse_args()
    summary = run_d5(Path(args.db))
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
