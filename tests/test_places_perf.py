"""Places perf helpers: hub-filtered POIs, diameter, persist cap, fixture bench."""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.load_fixtures import load_golden_fixtures
from lib.models import connect

from backend.services.cluster_places import (
    benchmark_list_places,
    diameter_km,
    diameter_pairwise_km,
    list_places,
    persist_clusters,
)

ETALON_BURGER = ["ancient_temple", "industrial_museum"]


def _load_fixture(rel: str) -> dict:
    return json.loads((ROOT / "fixtures" / rel).read_text(encoding="utf-8"))


class PlacesPerfTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.conn = connect(self.db_path)
        load_golden_fixtures(self.conn)
        self.conn.execute("DELETE FROM cluster")
        self.conn.commit()
        os.environ["BURGER_DB"] = self.db_path

    def tearDown(self) -> None:
        self.conn.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_hub_filtered_list_places_finds_etalon(self) -> None:
        etalon = _load_fixture("etalon_1.json")
        cid = etalon["cluster_id"]
        rest = cid[2:] if cid.startswith("c:") else cid
        self.assertNotIn(",", rest)
        self.assertEqual(len(etalon.get("hubs") or []), 1)
        body = list_places(self.conn, ETALON_BURGER, 100, limit=20)
        ids = [p["cluster_id"] for p in body["places"]]
        self.assertIn(cid, ids)
        card = next(p for p in body["places"] if p["cluster_id"] == cid)
        self.assertEqual(len(card["hubs"]), 1)
        self.assertEqual(set(card["coverage"]["matched"]), set(ETALON_BURGER))
        self.assertEqual(card["coverage"]["missing"], [])

    def test_persist_only_page_plus_existing(self) -> None:
        p_a = {
            "cluster_id": "c:a",
            "title": "A",
            "hubs": [{"hub_id": "a"}],
            "center": {"lat": 1.0, "lon": 2.0},
            "diameter_km": 1.0,
            "coverage": {"matched": [], "missing": []},
        }
        p_b = {
            "cluster_id": "c:b",
            "title": "B",
            "hubs": [{"hub_id": "b"}],
            "center": {"lat": 3.0, "lon": 4.0},
            "diameter_km": 2.0,
            "coverage": {"matched": [], "missing": []},
        }
        n1 = persist_clusters(self.conn, [p_b], 100, cap=1)
        self.assertEqual(n1, 1)
        n2 = persist_clusters(self.conn, [p_a, p_b], 100, cap=1)
        self.assertGreaterEqual(n2, 1)
        ids = {
            r["id"]
            for r in self.conn.execute("SELECT id FROM cluster WHERE radius_km = 100").fetchall()
        }
        self.assertEqual(ids, {"c:a", "c:b"})
        n3 = persist_clusters(self.conn, [p_a, p_b], 100, cap=1)
        self.assertEqual(n3, 0)

    def test_persist_page_cap_on_list_places(self) -> None:
        body = list_places(self.conn, ETALON_BURGER, 100, limit=1)
        self.assertEqual(len(body["places"]), 1)
        n = self.conn.execute("SELECT COUNT(*) AS n FROM cluster").fetchone()["n"]
        self.assertEqual(n, 1)
        self.assertEqual(
            self.conn.execute("SELECT id FROM cluster").fetchone()["id"],
            body["places"][0]["cluster_id"],
        )

    def test_diameter_hull_matches_pairwise(self) -> None:
        pois = []
        lat0 = 57.6
        lon0 = 39.8
        for i in range(50):
            ang = 2.0 * math.pi * i / 50.0
            pois.append(
                {
                    "id": "p%d" % i,
                    "lat": lat0 + 0.12 * math.sin(ang),
                    "lon": lon0 + 0.12 * math.cos(ang),
                }
            )
        d_pair = diameter_pairwise_km(pois)
        d_hull = diameter_km(pois, pairwise_max_n=0)
        self.assertGreater(d_pair, 0.0)
        self.assertAlmostEqual(d_hull, d_pair, places=6)

    def test_benchmark_golden_fixtures_prints_stats(self) -> None:
        stats = benchmark_list_places(self.conn, ETALON_BURGER, 100, limit=20)
        print("places_bench", stats)
        self.assertGreater(stats["hubs"], 0)
        self.assertGreater(stats["pois"], 0)
        self.assertGreater(stats["candidates"], 0)
        self.assertIn("ms", stats)
        self.assertGreaterEqual(stats["ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
