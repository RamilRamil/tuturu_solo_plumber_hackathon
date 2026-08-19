"""Stream B: POST /api/places. Local discs, no network."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.cluster_config import (
    ALLOWED_RADIUS_KM,
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_KM,
    load_ingredient_ids,
)
from backend.services.cluster_places import list_places, open_db

router = APIRouter()
COVERAGE_PATH = Path(os.environ.get("BURGER_COVERAGE") or "data/coverage.json")


class PlacesIn(BaseModel):
    ingredients: list[str] = Field(default_factory=list)
    radius_km: int = DEFAULT_RADIUS_KM
    limit: int = DEFAULT_LIMIT
    exclude_regions: list[str] = Field(default_factory=list)

    class Config:
        extra = "ignore"


def _validate(body: PlacesIn) -> None:
    if not body.ingredients:
        raise HTTPException(status_code=400, detail="empty ingredients")
    known = load_ingredient_ids()
    for item in body.ingredients:
        if item not in known:
            raise HTTPException(status_code=400, detail="unknown ingredient")
    if body.radius_km not in ALLOWED_RADIUS_KM:
        raise HTTPException(status_code=400, detail="invalid radius_km")


@router.post("/api/places")
def post_places(body: PlacesIn) -> dict[str, Any]:
    _validate(body)
    conn = open_db()
    try:
        return list_places(
            conn,
            body.ingredients,
            body.radius_km,
            body.limit,
            exclude_regions=body.exclude_regions,
        )
    finally:
        conn.close()


@router.get("/api/coverage")
def get_coverage() -> dict[str, Any]:
    path = COVERAGE_PATH
    if not path.is_file():
        return {
            "regions_loaded": [],
            "note": "coverage metadata missing; empty results outside the map are an ingest hole",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="invalid coverage.json")
    return data
