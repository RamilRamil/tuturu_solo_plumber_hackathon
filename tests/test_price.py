"""POST /api/price SSE. Etalon v2 is Uglich; priced legs live on backup/pair."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.load_fixtures import load_golden_fixtures
from lib.models import connect
from lib.tutu_mcp import check_resolve, extract_meta, price_is_absent

from backend.app import app
from backend.routers.price import PriceRequest, post_price
from backend.services.price import (
    ASCII_ORIGIN_GEO,
    PRICE_STATUS,
    UnknownCluster,
    add_days,
    cache_leg_issue,
    directed_leg,
    first_window_start,
    later_window_starts,
    live_tutu_enabled,
    load_cluster_row,
    match_origin_hub,
    open_mcp,
    pick_priced_offer,
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


def _dummy_request() -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/price",
        "raw_path": b"/api/price",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    return Request(scope, receive)


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
        os.environ.pop("BURGER_SC_PRICE_ACCEPTED", None)
        os.environ.pop("BURGER_PRICE_DEMO_PACE", None)
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
        self.uglich_id = self.etalon["cluster_id"]
        self.pair_id = self.etalon["almost_fits_pair_id"]
        self.priced_id = self.backup["cluster_id"]

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
            resp = await post_price(self._req(cluster_id, budget_scope), _dummy_request())
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
            await post_price(self._req("c:no-such-hub"), _dummy_request())

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_run())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "unknown hub")
        self.assertNotIn("event: warning", str(ctx.exception.detail))

    def test_etalon_id_is_uglich_not_places0_or_backup(self) -> None:
        uglich = self.uglich_id
        single = self.priced_id
        pair = self.pair_id
        self.assertNotEqual(uglich, single)
        self.assertNotEqual(uglich, pair)
        self.assertIn("\u0423\u0433\u043b\u0438\u0447", uglich)
        mcp = open_mcp(self.db_path)
        try:
            row = load_cluster_row(mcp.conn, uglich)
            self.assertEqual(row["id"], uglich)
            with self.assertRaises(UnknownCluster):
                load_cluster_row(mcp.conn, "c:no-such-hub")
        finally:
            mcp.close()
        resp_status, _headers, body = self._price(uglich)
        self.assertEqual(resp_status, 200)
        events = _parse_sse(body)
        done = [p for n, p in events if n == "done"]
        self.assertTrue(done)
        self.assertEqual(done[-1]["cluster_id"], uglich)
        self.assertNotEqual(done[-1]["cluster_id"], single)

    def test_g10_sse_resolved_leg_done_one_by_one(self) -> None:
        status, headers, body = self._price(self.priced_id)
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

    def test_uglich_sse_warning_no_fake_fares(self) -> None:
        status, headers, body = self._price(self.uglich_id)
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", (headers.get("content-type") or "").lower())
        events = _parse_sse(body)
        names = [n for n, _p in events]
        self.assertEqual(names[0], "resolved")
        self.assertEqual(names[-1], "done")
        codes = [p["code"] for n, p in events if n == "warning"]
        self.assertIn("no_route", codes)
        self.assertIn("not_sellable", codes)
        legs = [p for n, p in events if n == "leg"]
        for leg in legs:
            self.assertGreater(leg["price"], 0)
            self.assertNotEqual(leg["price"], 0)
        brs = [p for n, p in events if n == "breakdown"]
        if not legs:
            self.assertFalse(brs)
        else:
            self.assertTrue(brs)
            self.assertGreater(brs[0]["transport"], 0)
        self.assertEqual(events[-1][1]["cluster_id"], self.uglich_id)
        self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")

    def test_fixture_confirmed_not_sc_price_4342(self) -> None:
        status, _headers, body = self._price(
            self.priced_id, budget_scope="all"
        )
        self.assertEqual(status, 200)
        events = _parse_sse(body)
        brs = [p for n, p in events if n == "breakdown"]
        self.assertTrue(brs)
        self.assertEqual(brs[0]["price_status"], "fixture-confirmed")
        self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")

    def test_hotel_stay_total_not_times_nights(self) -> None:
        status, _headers, body = self._price(
            self.priced_id, budget_scope="all"
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

            req = self._price_body(self.uglich_id)
            list(iter_price_events(req, mcp))
            self.assertEqual(calls["n"], 0)
        finally:
            mcp.close()

    def test_checkout_url_passthrough_if_present(self) -> None:
        raw = '{"checkout_url": "https://www.tutu.ru/example?x=1&y=2"}'
        doc = json.loads(raw)
        from backend.services.price import checkout_url_from_obj

        self.assertEqual(doc["checkout_url"], checkout_url_from_obj(doc))

    def test_illegal_cluster_id_is_http_404_before_sse(self) -> None:
        async def _run():
            await post_price(self._req("not-a-cluster"), _dummy_request())

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_run())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "illegal cluster_id")
        self.assertNotIn("event: warning", str(ctx.exception.detail))

    def test_empty_cluster_table_still_prices(self) -> None:
        uglich = self.uglich_id
        backup = self.priced_id
        mcp = open_mcp(self.db_path)
        try:
            mcp.conn.execute("DELETE FROM cluster")
            mcp.conn.commit()
            row = load_cluster_row(mcp.conn, uglich)
            self.assertEqual(row["id"], uglich)
            row_b = load_cluster_row(mcp.conn, backup)
            self.assertEqual(row_b["id"], backup)
        finally:
            mcp.close()
        for cid in (uglich, backup):
            status, _headers, body = self._price(cid)
            self.assertEqual(status, 200)
            events = _parse_sse(body)
            self.assertEqual(events[0][0], "resolved")
            self.assertEqual(events[-1][0], "done")
            self.assertEqual(events[-1][1]["cluster_id"], cid)
            self.assertIn("event: resolved", body)

    def test_places_then_price_ok(self) -> None:
        uglich = self.uglich_id
        mcp = open_mcp(self.db_path)
        try:
            mcp.conn.execute("DELETE FROM cluster")
            mcp.conn.commit()
            row = load_cluster_row(mcp.conn, uglich)
            self.assertEqual(row["id"], uglich)
        finally:
            mcp.close()
        with TestClient(app) as client:
            res = client.post(
                "/api/places",
                json={
                    "ingredients": self.etalon["ingredients"],
                    "radius_km": 100,
                    "limit": 20,
                },
            )
            self.assertEqual(res.status_code, 200)
            ids = [p["cluster_id"] for p in res.json()["places"]]
            self.assertIn(uglich, ids)
        status, _headers, body = self._price(uglich)
        self.assertEqual(status, 200)
        events = _parse_sse(body)
        self.assertEqual(events[0][0], "resolved")
        self.assertEqual(events[-1][0], "done")
        self.assertEqual(events[-1][1]["cluster_id"], uglich)

    def test_zero_rub_not_treated_as_price(self) -> None:
        self.assertTrue(price_is_absent(0))
        self.assertIsNone(pick_priced_offer([{"transport": "etrain", "price": {"amount": 0}}]))
        self.assertEqual(cache_leg_issue(None), "no_route")
        os.environ["BURGER_LIVE_TUTU"] = "1"
        mcp = open_mcp(self.db_path)
        try:
            def fake(_name: str, args: dict) -> dict:
                dest = str(args.get("destination") or "")
                region = ""
                for row in mcp.conn.execute("SELECT * FROM hub"):
                    names = [row["name"] or "", row["resolved_name"] or ""]
                    if dest in names or any(dest.startswith(n) for n in names if n):
                        region = row["resolved_region"] or row["expected_region"] or row["subject"]
                        break
                body = {
                    "meta": {"to": {"name": dest or "x", "region": region or "x"}},
                    "variants": [{"transport": "etrain", "price": {"amount": 0}}],
                }
                return {
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(body, ensure_ascii=True)}]
                    }
                }

            mcp.call_tool = fake  # type: ignore[method-assign]
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.priced_id), mcp))
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            for leg in legs:
                self.assertGreater(leg["price"], 0)
                self.assertEqual(leg["source"], "cache")
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
            codes = [p["code"] for n, p in events if n == "warning"]
            self.assertIn("cache_fallback", codes)
            self.assertNotIn("no_price", codes)
        finally:
            mcp.close()
            os.environ.pop("BURGER_LIVE_TUTU", None)

    def test_cache_fallback_when_live_disabled_or_raises(self) -> None:
        self.assertFalse(live_tutu_enabled())
        mcp = open_mcp(self.db_path)
        try:
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.priced_id), mcp))
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            self.assertTrue(all(p["source"] == "cache" for p in legs))
            codes = [p["code"] for n, p in events if n == "warning"]
            self.assertNotIn("cache_fallback", codes)
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
        finally:
            mcp.close()

        os.environ["BURGER_LIVE_TUTU"] = "1"
        mcp = open_mcp(self.db_path)
        try:
            def boom(*_a, **_k):
                raise TimeoutError("tutu timeout")

            mcp.call_tool = boom  # type: ignore[method-assign]
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.priced_id), mcp))
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            self.assertTrue(all(p["source"] == "cache" for p in legs))
            codes = [p["code"] for n, p in events if n == "warning"]
            self.assertIn("cache_fallback", codes)
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
        finally:
            mcp.close()
            os.environ.pop("BURGER_LIVE_TUTU", None)

    def test_live_priced_hop_stays_fixture_confirmed(self) -> None:
        os.environ["BURGER_LIVE_TUTU"] = "1"
        os.environ.pop("BURGER_SC_PRICE_ACCEPTED", None)
        mcp = open_mcp(self.db_path)
        live_url = "https://www.tutu.ru/live-example?x=1&y=2"
        try:
            def fake(_name: str, args: dict) -> dict:
                dest = str(args.get("destination") or "")
                region = ""
                rname = dest or "x"
                for row in mcp.conn.execute("SELECT * FROM hub"):
                    names = [row["name"] or "", row["resolved_name"] or ""]
                    if dest in names or any(dest.startswith(n) for n in names if n):
                        region = row["resolved_region"] or row["expected_region"] or row["subject"]
                        rname = row["resolved_name"] or row["name"]
                        break
                body = {
                    "meta": {"to": {"name": rname, "region": region or "x"}},
                    "variants": [
                        {
                            "transport": "railway",
                            "price": {"amount": 1200},
                            "duration_min": 180,
                            "checkout_url": live_url,
                            "checkout_ref": {"transport": "railway"},
                        }
                    ],
                }
                return {
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(body, ensure_ascii=True)}]
                    }
                }

            mcp.call_tool = fake  # type: ignore[method-assign]
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.priced_id), mcp))
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            self.assertTrue(any(p["source"] == "live" for p in legs))
            for leg in legs:
                self.assertGreater(leg["price"], 0)
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
            brs = [p for n, p in events if n == "breakdown"]
            self.assertTrue(brs)
            self.assertEqual(brs[0]["price_status"], "fixture-confirmed")
            checkouts = [p for n, p in events if n == "checkout"]
            self.assertTrue(checkouts)
            urls = [it["checkout_url"] for it in checkouts[0]["items"]]
            self.assertIn(live_url, urls)
        finally:
            mcp.close()
            os.environ.pop("BURGER_LIVE_TUTU", None)

    def test_live_on_calls_tool_despite_route_cache(self) -> None:
        os.environ["BURGER_LIVE_TUTU"] = "1"
        os.environ.pop("BURGER_SC_PRICE_ACCEPTED", None)
        mcp = open_mcp(self.db_path)
        live_url = "https://www.tutu.ru/live-despite-cache"
        calls = {"n": 0}
        try:
            conn = mcp.conn
            geo_to_id = {}
            for row in conn.execute("SELECT * FROM hub"):
                geo_to_id[row["tutu_geo_id"] or ""] = row["id"]
            mow = geo_to_id.get("fixture-mow")
            yar = geo_to_id.get("fixture-yar")
            self.assertTrue(mow and yar)
            requested = first_window_start(self.etalon["month"])
            return_day = add_days(requested, max(0, int(self.etalon["days"]) - 1))
            payload = json.dumps(
                {
                    "variants": [
                        {
                            "transport": "railway",
                            "price": {"amount": 10},
                            "checkout_url": "https://www.tutu.ru/cache-should-lose",
                        }
                    ]
                },
                ensure_ascii=True,
            )
            for origin_hub, dest_hub, day in (
                (mow, yar, requested),
                (yar, mow, return_day),
            ):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO route_cache(
                      origin_hub, dest_hub, date, adults, pax_sig, payload_json, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        origin_hub,
                        dest_hub,
                        day,
                        1,
                        "",
                        payload,
                        "2026-08-19T00:00:00Z",
                    ),
                )
            conn.commit()

            def fake(_name: str, args: dict) -> dict:
                calls["n"] += 1
                dest = str(args.get("destination") or "")
                region = ""
                rname = dest or "x"
                for row in mcp.conn.execute("SELECT * FROM hub"):
                    names = [row["name"] or "", row["resolved_name"] or ""]
                    if dest in names or any(dest.startswith(n) for n in names if n):
                        region = row["resolved_region"] or row["expected_region"] or row["subject"]
                        rname = row["resolved_name"] or row["name"]
                        break
                body = {
                    "meta": {"to": {"name": rname, "region": region or "x"}},
                    "variants": [
                        {
                            "transport": "railway",
                            "price": {"amount": 1300},
                            "duration_min": 180,
                            "checkout_url": live_url,
                            "checkout_ref": {"transport": "railway"},
                        }
                    ],
                }
                return {
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(body, ensure_ascii=True)}]
                    }
                }

            mcp.call_tool = fake  # type: ignore[method-assign]
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.priced_id), mcp))
            self.assertGreater(calls["n"], 0)
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            self.assertTrue(any(p["source"] == "live" for p in legs))
            self.assertTrue(all(p["price"] != 10 for p in legs if p["source"] == "live"))
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
        finally:
            mcp.close()
            os.environ.pop("BURGER_LIVE_TUTU", None)

    def test_route_cache_uses_requested_day_not_date_probed(self) -> None:
        requested = first_window_start(self.etalon["month"])
        marker_url = "https://www.tutu.ru/cache-day-" + requested
        mcp = open_mcp(self.db_path)
        try:
            conn = mcp.conn
            geo_to_id = {}
            for row in conn.execute("SELECT * FROM hub"):
                geo_to_id[row["tutu_geo_id"] or ""] = row["id"]
            mow = geo_to_id.get("fixture-mow")
            yar = geo_to_id.get("fixture-yar")
            rostov = geo_to_id.get("fixture-rv")
            self.assertTrue(mow and yar and rostov)
            return_day = add_days(requested, max(0, int(self.etalon["days"]) - 1))
            hops = ((mow, yar, requested), (yar, rostov, requested), (rostov, mow, return_day))
            payload = json.dumps(
                {
                    "variants": [
                        {
                            "transport": "railway",
                            "price": {"amount": 4242},
                            "checkout_url": marker_url,
                            "checkout_ref": {"day": requested},
                        }
                    ]
                },
                ensure_ascii=True,
            )
            for origin_hub, dest_hub, day in hops:
                conn.execute(
                    """
                    UPDATE leg SET date_probed = ?, min_price = ?
                    WHERE origin_hub = ? AND dest_hub = ?
                    """,
                    ("2026-10-02", 1, origin_hub, dest_hub),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO route_cache(
                      origin_hub, dest_hub, date, adults, pax_sig, payload_json, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        origin_hub,
                        dest_hub,
                        day,
                        1,
                        "",
                        payload,
                        "2026-08-19T00:00:00Z",
                    ),
                )
            conn.commit()
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.pair_id), mcp))
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            for leg in legs:
                self.assertNotEqual(leg["date"], "2026-10-02")
                self.assertEqual(leg["price"], 4242)
                self.assertNotEqual(leg["price"], 1)
                self.assertEqual(leg["source"], "cache")
                self.assertNotIn("stale", leg)
            checkouts = [p for n, p in events if n == "checkout"]
            self.assertTrue(checkouts)
            urls = [it["checkout_url"] for it in checkouts[0]["items"]]
            self.assertTrue(urls)
            self.assertTrue(all(u == marker_url for u in urls))
        finally:
            mcp.close()

    def test_return_fallback_sets_recovered(self) -> None:
        mcp = open_mcp(self.db_path)
        try:
            conn = mcp.conn
            geo_to_id = {}
            for row in conn.execute("SELECT * FROM hub"):
                geo_to_id[row["tutu_geo_id"] or ""] = row["id"]
            mow = geo_to_id.get("fixture-mow")
            yar = geo_to_id.get("fixture-yar")
            rostov = geo_to_id.get("fixture-rv")
            self.assertTrue(mow and yar and rostov)
            conn.execute(
                "DELETE FROM leg WHERE origin_hub = ? AND dest_hub = ?",
                (rostov, mow),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO leg(
                  origin_hub, dest_hub, date_probed, modes, min_price,
                  duration_min, latency_ms, checked_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    yar,
                    mow,
                    "2026-10-11",
                    "railway",
                    500,
                    None,
                    1,
                    "2026-08-19T00:00:00Z",
                    "ok",
                ),
            )
            conn.commit()
            from backend.services.price import iter_price_events

            events = list(iter_price_events(self._price_body(self.pair_id), mcp))
            recovered = [
                p for n, p in events if n == "warning" and p.get("recovered") is True
            ]
            self.assertTrue(recovered)
            self.assertEqual(recovered[0]["code"], "no_route")
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            self.assertEqual(legs[-1]["from_hub"], yar)
            self.assertEqual(legs[-1]["to_hub"], mow)
        finally:
            mcp.close()

    def test_child_fare_unverified_warning(self) -> None:
        mcp = open_mcp(self.db_path)
        try:
            from backend.services.price import iter_price_events

            req = self._price_body(self.priced_id)
            req["children_ages"] = [5]
            events = list(iter_price_events(req, mcp))
            codes = [p["code"] for n, p in events if n == "warning"]
            self.assertIn("child_fare_unverified", codes)
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
        finally:
            mcp.close()

    def test_slow_price_does_not_block_healthz(self) -> None:
        orig = price_svc.quote_directed_hop
        entered = threading.Event()

        def slow_hop(*args, **kwargs):
            entered.set()
            time.sleep(2.0)
            return orig(*args, **kwargs)

        price_svc.quote_directed_hop = slow_hop  # type: ignore[method-assign]
        try:
            body = self._price_body(self.priced_id)

            async def _run():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    async def consume():
                        async with ac.stream("POST", "/api/price", json=body) as resp:
                            async for _chunk in resp.aiter_bytes():
                                pass

                    task = asyncio.create_task(consume())
                    ok = await asyncio.to_thread(entered.wait, 5.0)
                    self.assertTrue(ok)
                    t0 = time.monotonic()
                    res = await ac.get("/healthz")
                    elapsed = time.monotonic() - t0
                    await task
                    return res.status_code, elapsed

            status, elapsed = asyncio.run(_run())
            self.assertEqual(status, 200)
            self.assertLess(elapsed, 1.0)
        finally:
            price_svc.quote_directed_hop = orig

    @unittest.skipUnless(
        (os.environ.get("BURGER_LIVE_NET") or "").strip().lower() in ("1", "true", "yes", "on"),
        "live tutu network not enabled",
    )
    def test_live_tutu_network_optional(self) -> None:
        os.environ["BURGER_LIVE_TUTU"] = "1"
        os.environ.pop("BURGER_SC_PRICE_ACCEPTED", None)
        try:
            status, _headers, body = self._price(self.uglich_id)
            self.assertEqual(status, 200)
            events = _parse_sse(body)
            self.assertEqual(events[0][0], "resolved")
            self.assertEqual(events[-1][0], "done")
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
            codes = [p["code"] for n, p in events if n == "warning"]
            self.assertTrue("no_route" in codes or "not_sellable" in codes, codes)
            for _n, payload in events:
                if _n == "leg":
                    self.assertGreater(payload["price"], 0)

            status, _headers, body = self._price(self.priced_id)
            self.assertEqual(status, 200)
            events = _parse_sse(body)
            self.assertEqual(events[0][0], "resolved")
            self.assertEqual(events[-1][0], "done")
            self.assertEqual(events[-1][1]["price_status"], "fixture-confirmed")
            self.assertNotEqual(events[-1][1]["price_status"], "live")
            legs = [p for n, p in events if n == "leg"]
            self.assertTrue(legs)
            for leg in legs:
                self.assertGreater(leg["price"], 0)
            checkouts = [p for n, p in events if n == "checkout"]
            for item in checkouts[0]["items"] if checkouts else []:
                url = item.get("checkout_url") or ""
                self.assertTrue(url.startswith("https://"))
                host = url.split("/")[2]
                self.assertTrue(host.endswith("tutu.ru"))
        finally:
            os.environ.pop("BURGER_LIVE_TUTU", None)


if __name__ == "__main__":
    unittest.main()
