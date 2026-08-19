"""AI input edge: POST /api/parse. Free text -> {ingredients, radius_km, unmatched}.

Pre-phase-1 seam: the only network call here is to the model, never to Tutu.
Never used by the etalon or by regression tests - those post {ingredients}
straight to /api/places (knowledge/invariants/etalon-bypasses-llm.md).

Contract:
  in : {"text": "<phrase>", "radius_km"?: int}
  out: {"ingredients": [str], "radius_km": int, "unmatched": [str]}

Fallback (no OPENROUTER_API_KEY, timeout, HTTP error, garbage JSON): HTTP 200 with
{"ingredients": [], "radius_km": <default>, "unmatched": [<original text>]}.
Never 500 - the UI falls back to picking chips by hand.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.cluster_config import DEFAULT_RADIUS_KM
from backend.services.parse_intent import fallback, parse_intent

router = APIRouter()


class ParseIn(BaseModel):
    text: str = Field(default="")
    radius_km: int | None = None

    class Config:
        extra = "ignore"


@router.post("/api/parse")
def post_parse(body: ParseIn) -> dict[str, Any]:
    try:
        return parse_intent(body.text, body.radius_km)
    except Exception:
        return fallback(body.text, body.radius_km)


@router.get("/api/parse/health")
def parse_health() -> dict[str, Any]:
    from backend.services.parse_intent import _api_key

    return {"enabled": bool(_api_key()), "default_radius_km": DEFAULT_RADIUS_KM}
