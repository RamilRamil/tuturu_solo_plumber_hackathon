"""POST /api/price SSE. Etalon cluster_id from fixtures/etalon_1.json, not places[0]."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException

from lib.load_fixtures import load_golden_fixtures
from lib.models import connect
from lib.tutu_mcp import check_resolve, extract_meta, price_is_absent

from backend.routers.price import PriceRequest, post_price
from backend.services.price import (
    ASCII_ORIGIN_GEO,
    PRICE_STATUS,
    UnknownCluster,
    directed_leg,
    first_window_start,
    later_window_starts,
    live_tutu_enabled,
    load_cluster_row,
    match_origin_hub,
    open_mcp,
    stay_total_from_hotel_payload,
)
import backend.routers.price as price_router
import backend.services.price as price_svc


def _load_json(rel: str) -> dict:
    return json.loads((ROOT / "fixtures" / rel).read_text(encoding="utf-8"))


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    name = "message"
    data: list[str] = []
    for line in body.splitlines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
        elif line.strip() == "":
            if data:
                events.append((name, json.loads("\n".join(data))))
            name = "message"
            data = []
    if data:
        events.append((name, json.loads("\n".join(data))))
    return events


class PriceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        conn = connect(self.db_path)
        try:
            load_golden_fixtures(conn)
        finally:
            conn.close()
        os.environ["BURGER_DB"] = self.db_path
        os.environ.pop("BURGER_LIVE_TUTU", None)
        self._leg_pause = price_svc.FIRST_LEG_PAUSE_S
        self._evt_pause = price_svc.EVENT_PAUSE_S
        self._r_leg = price_router.FIRST_LEG_PAUSE_S
        self._r_evt = price_router.EVENT_PAUSE_S
        price_svc.FIRST_LEG_PAUSE_S = 0
        price_svc.EVENT_PAUSE_S = 0
        price_router.FIRST_LEG_PAUSE_S = 0
        price_router.EVENT_PAUSE_S = 0
        self.etalon = _load_json("etalon_1.json")
        self.backup = _load_json("backup_single_hub.json")

    def tearDown(self) -> None:
        price_svc.FIRST_LEG_PAUSE_S = self._leg_pause
        price_svc.EVENT_PAUSE_S = self._evt_pause
        price_router.FIRST_LEG_PAUSE_S = self._r_leg
        price_router.EVENT_PAUSE_S = self._r_evt
        os.environ.pop("BURGER_DB", None)
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _req(self, cluster_id: str, budget_scope: str = "transport") -> PriceRequest:
        return PriceRequest(
            cluster_id=cluster_id,
            origin=self.etalon["origin"],
            days=int(self.etalon["days"]),
            month=self.etalon["month"],
            adults=int(self.etalon["adults"]),
            children_ages=[],
            budget_scope=budget_scope,
        )

    def _price(self, cluster_id: str, budget_scope: str = "transport") -> tuple[int, dict, str]:
        async def _run():
            resp = await post_price(self._req(cluster_id, budget_scope))
            chunks: list[str] = []
            async for part in resp.body_iterator:
                if isinstance(part, bytes):
                    chunks.append(part.decode("utf-8"))
                else:
                    chunks.append(str(part))
            return resp.media_type or "", dict(resp.headers), "".join(chunks)

        media, headers, body = asyncio.run(_run())
        return 200, {"content-type": media, **{k.lower(): v for k, v in headers.items()}}, body

    def _price_body(self, cluster_id: str, budget_scope: str = "transport") -> dict:
        return {
            "cluster_id": cluster_id,
            "origin": self.etalon["origin"],
            "days": int(self.etalon["days"]),
            "month": self.etalon["month"],
            "adults": int(self.etalon["adults"]),
            "children_ages": [],
            "budget_scope": budget_scope,
        }

    def test_unknown_cluster_is_http_404_not_sse(self) -> None:
        async def _run():
            await post_price(self._req("c:no-such-hub"))

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_run())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertNotIn("event: warning", str(ctx.exception.detail))

    def test_etalon_id_is_pair_not_places0_or_backup(self) -> None:
        pair = self.etalon["cluster_id"]
        single = self.backup["cluster_id"]
        self.assertNotEqual(pair, single)
        self.assertIn(",", pair)
        mcp = open_mcp(self.db_path)
        try:
            row = load_cluster_row(mcp.conn, pair)
            self.assertEqual(row["id"], pair)
            with self.assertRaises(UnknownCluster):
                load_cluster_row(mcp.conn, "c:no-such-hub")
        finally:
            mcp.close()
        resp_status, headers, body = self._price(pair)
        self.assertEqual(resp_status, 200)
        events = _parse_sse(body)
        done = [p for n, p in events if n == "done"]
        self.assertTrue(done)
        self.assertEqual(done[-1]["cluster_id"], pair)
        self.assertNotEqual(done[-1]["cluster_id"], single)

    def test_g10_sse_resolved_leg_done_one_by_one(self) -> None:
        status, headers, body = self._price(self.etalon["cluster_id"])
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", (headers.get("content-type") or "").lower())
        events = _parse_sse(body)
        names = [n for n, _p in events]
        self.assertGreaterEqual(len(names), 3)
        self.assertEqual(names[0], "resolved")
        self.assertIn("leg", names)
        self.assertEqual(names[-1], "done")
        self.assertLess(names.index("leg"), names.index("done"))
        self.assertIn("event: resolved", body)
        self.assertIn("event: leg", body)
        self.assertIn("event: done", body)
        frames = [p for p in body.split("\n\n") if p.strip()]
        self.assertGreaterEqual(len(frames), 3)
        resolved = events[0][1]
        self.assertEqual(resolved["origin"]["guard"], "ok")
        first_leg = next(p for n, p in events if n == "leg")
        self.assertGreater(first_leg["price"], 0)
        done = events[-1][1]
        self.assertEqual(done["price_status"], PRICE_STATUS)
        self.assertEqual(done["price_status"], "fixture-confirmed")

    def test_fixture_confirmed_not_sc_price_4342(self) -> None:
        status, _headers, body = self._price(
            self.etalon["cluster_id"], budget_scope="all"
        )
        self.assertEqual(status, 200)
        events = _parse_sse(body)
        brs = [p for n, p in events if n == "breakdown"]
        self.assertTrue(brs)
        self.assertEqual(brs[0]["price_status"], "fixture-confirmed")
        self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")

    def test_hotel_stay_total_not_times_nights(self) -> None:
        status, _headers, body = self._price(
            self.etalon["cluster_id"], budget_scope="all"
        )
        self.assertEqual(status, 200)
        events = _parse_sse(body)
        hotels = [p for n, p in events if n == "hotel"]
        self.assertTrue(hotels)
        for h in hotels:
            self.assertEqual(h["price_basis"], "stay_total")
            self.assertGreater(h["min_price"], 0)
            if h["nights"] > 1:
                self.assertNotEqual(h["min_price"], 750 * h["nights"])

    def test_moscow_ascii_origin_hint(self) -> None:
        self.assertIn("moscow", ASCII_ORIGIN_GEO)
        mcp = open_mcp(self.db_path)
        try:
            row = match_origin_hub(mcp.conn, "Moscow")
            self.assertIsNotNone(row)
        finally:
            mcp.close()

    def test_reverse_leg_is_separate_row(self) -> None:
        mcp = open_mcp(self.db_path)
        try:
            conn = mcp.conn
            tver = None
            torzhok = None
            mow = None
            for row in conn.execute("SELECT * FROM hub"):
                geo = row["tutu_geo_id"] or ""
                if geo == "fixture-tver":
                    tver = row["id"]
                elif geo == "fixture-torzhok":
                    torzhok = row["id"]
                elif geo == "fixture-mow":
                    mow = row["id"]
            self.assertTrue(tver and torzhok and mow)
            fwd = directed_leg(conn, tver, torzhok, "2026-10-09")
            rev = directed_leg(conn, torzhok, mow, "2026-10-09")
            self.assertIsNotNone(fwd)
            self.assertEqual(fwd["status"], "ok")
            self.assertIsNotNone(rev)
            self.assertEqual(rev["status"], "no_route")
            self.assertNotEqual(fwd["status"], rev["status"])
        finally:
            mcp.close()

    def test_guard_blocks_foreign_region_before_price(self) -> None:
        doc = _load_json("tutu/rostov.json")
        live = _load_json("raw/g5_yaroslavl_rostov.json")
        ok, reason = check_resolve(
            extract_meta(live),
            doc["expected_name"],
            doc["expected_region"],
        )
        self.assertFalse(ok)
        src = inspect.getsource(price_svc)
        self.assertNotIn("def check_resolve", src)
        src_r = inspect.getsource(price_router)
        self.assertNotIn("def check_resolve", src_r)

    def test_zero_price_is_absence(self) -> None:
        self.assertTrue(price_is_absent(0))
        payload = {"hotels": [{"min_price": 750, "stay": {"nights": 3}}]}
        self.assertEqual(stay_total_from_hotel_payload(payload), 750)
        self.assertNotEqual(stay_total_from_hotel_payload(payload), 750 * 3)

    def test_lazy_windows_do_not_fan_out_without_live(self) -> None:
        self.assertFalse(live_tutu_enabled())
        first = first_window_start(self.etalon["month"])
        later = later_window_starts(self.etalon["month"], first)
        self.assertTrue(later)
        mcp = open_mcp(self.db_path)
        calls = {"n": 0}

        def boom(*_a, **_k):
            calls["n"] += 1
            raise AssertionError("live tutu must not run on fixture path")

        mcp.call_tool = boom  # type: ignore[method-assign]
        try:
            from backend.services.price import iter_price_events

            req = self._price_body(self.etalon["cluster_id"])
            list(iter_price_events(req, mcp))
            self.assertEqual(calls["n"], 0)
        finally:
            mcp.close()

    def test_checkout_url_passthrough_if_present(self) -> None:
        raw = '{"checkout_url": "https://www.tutu.ru/example?x=1&y=2"}'
        doc = json.loads(raw)
        from backend.services.price import checkout_url_from_obj

        self.assertEqual(doc["checkout_url"], checkout_url_from_obj(doc))


if __name__ == "__main__":
    unittest.main()
