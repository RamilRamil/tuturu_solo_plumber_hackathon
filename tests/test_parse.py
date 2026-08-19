"""POST /api/parse: mocked model only. No live network.

Invariant: etalon / regression still post {ingredients} to /api/places and
never import parse_intent (knowledge/invariants/etalon-bypasses-llm.md).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app import app


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            name: os.environ.get(name)
            for name in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "BURGER_PARSE_MODEL")
        }
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("BURGER_PARSE_MODEL", None)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_empty_openrouter_key_fallback_200(self) -> None:
        os.environ["OPENROUTER_API_KEY"] = ""
        with patch("backend.services.parse_intent.httpx.post") as post:
            res = self.client.post("/api/parse", json={"text": "temples nearby"})
            post.assert_not_called()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["ingredients"], [])
        self.assertIn("unmatched", body)
        self.assertEqual(body["unmatched"], ["temples nearby"])

    def test_missing_openrouter_key_fallback_200(self) -> None:
        os.environ.pop("OPENROUTER_API_KEY", None)
        with patch("backend.services.parse_intent.httpx.post") as post:
            res = self.client.post("/api/parse", json={"text": "art museums"})
            post.assert_not_called()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["ingredients"], [])

    def test_phrase_filters_unknown_ids_via_validate(self) -> None:
        fake = json.dumps(
            {
                "ingredients": ["ancient_temple", "not_a_real_id", "artwork"],
                "radius_hint": 50,
            }
        )
        with patch("backend.services.parse_intent.call_model", return_value=fake) as mocked:
            with patch("backend.services.parse_intent.httpx.post") as post:
                res = self.client.post(
                    "/api/parse",
                    json={"text": "old temples and some art nearby"},
                )
                post.assert_not_called()
            mocked.assert_called_once()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["ingredients"], ["ancient_temple", "artwork"])
        self.assertEqual(body["unmatched"], ["not_a_real_id"])
        self.assertEqual(body["radius_km"], 50)

    def test_call_model_openrouter_shape_mocked_httpx(self) -> None:
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        captured: dict[str, object] = {}

        def fake_post(url: str, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return _FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": json_dumps_safe(
                                    {
                                        "ingredients": ["ancient_temple"],
                                        "radius_hint": None,
                                    }
                                )
                            }
                        }
                    ]
                },
            )

        from backend.services.parse_intent import call_model

        with patch("backend.services.parse_intent.httpx.post", side_effect=fake_post):
            raw = call_model("temples", "system prompt")
        self.assertIsNotNone(raw)
        self.assertEqual(captured["url"], "https://openrouter.ai/api/v1/chat/completions")
        headers = captured["headers"]
        assert isinstance(headers, dict)
        self.assertEqual(headers["Authorization"], "Bearer test-key-not-real")
        self.assertNotIn("x-api-key", headers)
        payload = captured["json"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "google/gemini-2.5-flash")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(captured["timeout"], 5.0)

    def test_httpx_error_fallback_never_500(self) -> None:
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        with patch(
            "backend.services.parse_intent.httpx.post",
            return_value=_FakeResponse(429, {"error": "rate"}),
        ):
            res = self.client.post("/api/parse", json={"text": "temples"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["ingredients"], [])

    def test_garbage_model_json_fallback_200(self) -> None:
        with patch("backend.services.parse_intent.call_model", return_value="not json"):
            res = self.client.post("/api/parse", json={"text": "temples"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["ingredients"], [])

    def test_etalon_file_does_not_import_parse(self) -> None:
        src = (ROOT / "tests" / "test_places.py").read_text(encoding="utf-8")
        self.assertNotIn("parse_intent", src)
        self.assertNotIn("/api/parse", src)
        self.assertNotIn("backend.routers.parse", src)
        self.assertNotIn("backend.services.parse_intent", src)
        self.assertIn("/api/places", src)
        self.assertIn('json={"ingredients":', src)
        places_src = (ROOT / "backend" / "routers" / "places.py").read_text(encoding="utf-8")
        self.assertNotIn("parse_intent", places_src)
        self.assertNotIn("/api/parse", places_src)


def json_dumps_safe(data: object) -> str:
    return json.dumps(data, ensure_ascii=True)


if __name__ == "__main__":
    unittest.main()
