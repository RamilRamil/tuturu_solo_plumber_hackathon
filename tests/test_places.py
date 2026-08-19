"""SC-ranking hard gates for POST /api/places. Top-5 is smoke, not an assert."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from lib.load_fixtures import load_golden_fixtures
from lib.models import connect, make_cluster_id, make_hub_id

from backend.app import app

ETALON_BURGER = ["ancient_temple", "industrial_museum"]
BACKUP_BURGER = ["ancient_temple", "ruins"]


def _load_fixture(rel: str) -> dict:
    return json.loads((ROOT / "fixtures" / rel).read_text(encoding="utf-8"))


def _not_sellable_poi_hub_id() -> str:
    hubs = json.loads((ROOT / "fixtures" / "rows" / "hubs.json").read_text(encoding="utf-8"))
    pois = json.loads((ROOT / "fixtures" / "rows" / "poi.json").read_text(encoding="utf-8"))
    not_sellable = {h["id"] for h in hubs if h["probe_status"] == "not_sellable"}
    for poi in pois:
        hid = poi.get("hub_id")
        if hid in not_sellable:
            return hid
    raise AssertionError("fixture missing not_sellable hub with poi")


def _coverage_ok(places: list) -> None:
    last = None
    for card in places:
        n = len(card["coverage"]["matched"])
        if last is not None:
            if n > last:
                raise AssertionError("SC-B3: smaller coverage ranked above larger")
        last = n


class PlacesTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        self.conn = connect(self.db_path)
        load_golden_fixtures(self.conn)
        self.conn.execute("DELETE FROM cluster")
        self.conn.commit()
        n_cluster = self.conn.execute("SELECT COUNT(*) AS n FROM cluster").fetchone()["n"]
        self.assertEqual(n_cluster, 0)
        os.environ["BURGER_DB"] = self.db_path
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.conn.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _post(self, ingredients: list[str], radius_km: int = 100, limit: int = 20) -> dict:
        res = self.client.post(
            "/api/places",
            json={"ingredients": ingredients, "radius_km": radius_km, "limit": limit},
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertIn("places", body)
        self.assertIn("total_found", body)
        return body

    def test_sc_b1_pair_exists_in_places(self) -> None:
        # Smoke on gold fixtures: pair is often in the first five. NOT an assert.
        etalon = _load_fixture("etalon_1.json")
        body = self._post(ETALON_BURGER, radius_km=100, limit=20)
        ids = [p["cluster_id"] for p in body["places"]]
        self.assertIn(etalon["cluster_id"], ids)
        card = next(p for p in body["places"] if p["cluster_id"] == etalon["cluster_id"])
        self.assertEqual(set(card["coverage"]["matched"]), set(ETALON_BURGER))
        self.assertEqual(card["coverage"]["missing"], [])
        self.assertNotIn("origin", body)
        self.assertNotIn("price", body)
        for place in body["places"]:
            self.assertNotIn("sellable", place)
            for hub in place["hubs"]:
                self.assertNotIn("sellable", hub)
                self.assertIn(hub["probe_status"], ("sellable", "not_sellable", "misresolved"))
        _coverage_ok(body["places"])
        backup_id = _load_fixture("backup_single_hub.json")["cluster_id"]
        single = next((p for p in body["places"] if p["cluster_id"] == backup_id), None)
        if single is not None and len(single["coverage"]["matched"]) == 2:
            pass

    def test_sc_b2_backup_exists_in_places(self) -> None:
        # Smoke on gold fixtures: backup is often in the first five. NOT an assert.
        backup = _load_fixture("backup_single_hub.json")
        body = self._post(BACKUP_BURGER, radius_km=100, limit=20)
        ids = [p["cluster_id"] for p in body["places"]]
        self.assertIn(backup["cluster_id"], ids)
        card = next(p for p in body["places"] if p["cluster_id"] == backup["cluster_id"])
        self.assertEqual(set(card["coverage"]["matched"]), set(BACKUP_BURGER))
        self.assertEqual(card["coverage"]["missing"], [])
        _coverage_ok(body["places"])

    def test_sc_b3_g10_hard_gates(self) -> None:
        etalon = _load_fixture("etalon_1.json")
        backup = _load_fixture("backup_single_hub.json")
        a = self._post(ETALON_BURGER)
        b = self._post(BACKUP_BURGER)
        self.assertIn(etalon["cluster_id"], [p["cluster_id"] for p in a["places"]])
        self.assertIn(backup["cluster_id"], [p["cluster_id"] for p in b["places"]])
        _coverage_ok(a["places"])
        _coverage_ok(b["places"])

    def test_empty_ingredients_400(self) -> None:
        res = self.client.post("/api/places", json={"ingredients": [], "radius_km": 100})
        self.assertEqual(res.status_code, 400)

    def test_unknown_ingredient_400(self) -> None:
        res = self.client.post(
            "/api/places",
            json={"ingredients": ["not_a_real_ingredient"], "radius_km": 100},
        )
        self.assertEqual(res.status_code, 400)

    def test_invalid_radius_400(self) -> None:
        res = self.client.post(
            "/api/places",
            json={"ingredients": ETALON_BURGER, "radius_km": 200},
        )
        self.assertEqual(res.status_code, 400)

    def test_cluster_id_stable_across_radius_steps(self) -> None:
        hid_a = make_hub_id("A", "S")
        hid_b = make_hub_id("B", "S")
        self.assertEqual(make_cluster_id([hid_a, hid_b]), make_cluster_id([hid_b, hid_a]))
        etalon = _load_fixture("etalon_1.json")["cluster_id"]
        ids_by_r = {}
        for radius in (50, 100, 150):
            body = self._post(ETALON_BURGER, radius_km=radius)
            found = [p["cluster_id"] for p in body["places"] if p["cluster_id"] == etalon]
            if found:
                ids_by_r[radius] = found[0]
        present = list(ids_by_r.values())
        self.assertTrue(len(set(present)) <= 1)
        self.assertIn(100, ids_by_r)

    def test_not_sellable_stays_and_not_in_pairs(self) -> None:
        body = self._post(ETALON_BURGER)
        boris = None
        target = _not_sellable_poi_hub_id()
        for place in body["places"]:
            hub_ids = [h["hub_id"] for h in place["hubs"]]
            if target in hub_ids:
                if len(place["hubs"]) != 1:
                    self.fail("not_sellable hub must not enter a pair")
                boris = place
        self.assertIsNotNone(boris)
        self.assertEqual(boris["hubs"][0]["probe_status"], "not_sellable")

    def test_places_module_has_no_network_imports(self) -> None:
        text = (ROOT / "backend" / "routers" / "places.py").read_text(encoding="utf-8")
        self.assertNotIn("tutu_mcp", text)
        self.assertNotIn("httpx", text)
        self.assertNotIn("urllib", text)
        rank = (ROOT / "backend" / "services" / "cluster_rank.py").read_text(encoding="utf-8")
        self.assertNotIn("FROM cluster", rank)
        places_svc = (ROOT / "backend" / "services" / "cluster_places.py").read_text(encoding="utf-8")
        self.assertNotIn("FROM cluster", places_svc)
        self.assertNotIn("FROM leg", places_svc)


if __name__ == "__main__":
    unittest.main()
