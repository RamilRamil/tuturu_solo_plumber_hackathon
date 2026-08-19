"""Guard §7 + G3 region source. Fixtures are fixture-confirmed field-test facts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.load_fixtures import load_golden_fixtures
from lib.models import connect, make_cluster_id, make_hub_id
from lib.tutu_mcp import (
    SOURCE_HANDBOOK,
    SOURCE_OSM,
    TutuMcp,
    args_hash,
    check_resolve,
    extract_meta,
    iter_name_attempts,
    price_is_absent,
    resolve_expected_region,
    sellable_modes_from_meta,
)


def _load_fixture(rel: str) -> dict:
    return json.loads((ROOT / "fixtures" / rel).read_text(encoding="utf-8"))


def _g5(rel: str) -> dict:
    return _load_fixture("raw/" + rel)


class GuardTests(unittest.TestCase):
    def test_rostov_query_is_red(self) -> None:
        doc = _load_fixture("tutu/rostov.json")
        live = _g5("g5_yaroslavl_rostov.json")
        ok, reason = check_resolve(
            extract_meta(live),
            doc["expected_name"],
            doc["expected_region"],
        )
        self.assertFalse(ok)
        self.assertIn(reason, ("region_mismatch", "missing_region"))
        self.assertFalse(doc["want_ok"])

    def test_rostov_veliky_is_green(self) -> None:
        doc = _load_fixture("tutu/rostov_veliky.json")
        live = _g5("g5_yaroslavl_rostov_veliky.json")
        ok, reason = check_resolve(
            extract_meta(live),
            doc["expected_name"],
            doc["expected_region"],
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")
        self.assertTrue(doc["want_ok"])

    def test_veliky_novgorod_is_red(self) -> None:
        doc = _load_fixture("tutu/veliky_novgorod.json")
        live = _g5("g5_moscow_veliky_novgorod.json")
        ok, _reason = check_resolve(
            extract_meta(live),
            doc["expected_name"],
            doc["expected_region"],
        )
        self.assertFalse(ok)

    def test_g3_outside_handbook_guard_green(self) -> None:
        doc = _load_fixture("g3_outside_handbook.json")
        region, source = resolve_expected_region(
            bool(doc["in_handbook"]),
            doc["handbook_subject"],
            doc["osm_admin4_name"],
        )
        self.assertEqual(source, SOURCE_OSM)
        self.assertEqual(source, doc["want_source"])
        self.assertEqual(region, doc["expected_region"])
        ok, reason = check_resolve(
            extract_meta(doc["payload"]),
            doc["expected_name"],
            region or "",
        )
        self.assertTrue(ok, reason)

    def test_handbook_subject_wins_over_osm(self) -> None:
        region, source = resolve_expected_region(True, "A oblast", "B krai")
        self.assertEqual(source, SOURCE_HANDBOOK)
        self.assertEqual(region, "A oblast")


class ProbeAndCacheTests(unittest.TestCase):
    def test_misresolved_not_collapsed_to_not_sellable(self) -> None:
        doc = _load_fixture("tutu/rostov.json")
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        mcp = TutuMcp(tmp.name)
        try:
            load_golden_fixtures(mcp.conn)
            subject = doc["expected_region"]
            name = doc["expected_name"]
            attempts = iter_name_attempts(name, subject)
            payload = doc["payload"]
            for query in attempts:
                mcp._cache_put(
                    "search_multitransport",
                    args_hash(
                        "search_multitransport",
                        {
                            "origin": doc["origin"],
                            "destination": query,
                            "departure_date": "2026-10-09",
                            "adults": 1,
                            "page_size": 1,
                        },
                    ),
                    {
                        "origin": doc["origin"],
                        "destination": query,
                        "departure_date": "2026-10-09",
                        "adults": 1,
                        "page_size": 1,
                    },
                    payload,
                )
            outcome = mcp.probe_destination(
                origin=doc["origin"],
                name=name,
                subject=subject,
                expected_region=subject,
                departure_date="2026-10-09",
            )
            self.assertEqual(outcome.status, "misresolved")
            self.assertNotEqual(outcome.status, "not_sellable")
        finally:
            mcp.close()

    def test_zero_price_is_absence(self) -> None:
        self.assertTrue(price_is_absent(0))
        self.assertTrue(price_is_absent(0.0))
        self.assertFalse(price_is_absent(659))
        live = extract_meta(_g5("g5_yaroslavl_rostov_veliky.json"))
        modes = sellable_modes_from_meta(live)
        self.assertIn("railway", modes.split(",") if modes else [])
        self.assertNotIn("etrain", modes.split(",") if modes else [])

    def test_cluster_id_stable_across_radius(self) -> None:
        hid_a = make_hub_id("A", "S")
        hid_b = make_hub_id("B", "S")
        cid_50 = make_cluster_id([hid_a, hid_b])
        cid_100 = make_cluster_id([hid_b, hid_a])
        self.assertEqual(cid_50, cid_100)
        self.assertTrue(cid_50.startswith("c:"))
        conn = connect(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
        try:
            load_golden_fixtures(conn)
            rows = conn.execute("SELECT DISTINCT id FROM cluster").fetchall()
            ids = {r["id"] for r in rows}
            etalon = _load_fixture("etalon_1.json")["cluster_id"]
            backup = _load_fixture("backup_single_hub.json")["cluster_id"]
            self.assertIn(etalon, ids)
            self.assertIn(backup, ids)
            radii = [
                r["radius_km"]
                for r in conn.execute(
                    "SELECT radius_km FROM cluster WHERE id = ? ORDER BY radius_km",
                    (etalon,),
                ).fetchall()
            ]
            self.assertEqual(radii, [50, 100, 150])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
