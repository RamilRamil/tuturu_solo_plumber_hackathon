"""Merge coverage.json across OSM region waves. ASCII literals only.

Not wired into parse_osm.py; integrator attaches this after the data-agent merge.
Slug is the stable region identity. Label is display text. Never match EN/RU
substrings to decide identity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATUS_LOADED = "loaded"
STATUS_FAILED = "failed"


def empty_coverage_state() -> dict[str, Any]:
    return {
        "regions": [],
        "regions_loaded": [],
        "poi_count_db": 0,
        "poi_count_wave": 0,
    }


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_region(item: dict[str, Any]) -> dict[str, Any] | None:
    slug = item.get("slug")
    if not isinstance(slug, str) or not slug:
        return None
    label = item.get("label")
    if not isinstance(label, str) or not label:
        label = slug
    status = item.get("status")
    if status != STATUS_LOADED:
        status = STATUS_FAILED
    return {
        "slug": slug,
        "label": label,
        "status": status,
        "poi_wave": _as_int(item.get("poi_wave"), 0),
    }


def _regions_from_legacy_loaded(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Identity migrate regions_loaded strings: slug = label = the string."""
    loaded = raw.get("regions_loaded")
    if not isinstance(loaded, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in loaded:
        if not isinstance(item, str) or not item or item in seen:
            continue
        seen.add(item)
        out.append(
            {
                "slug": item,
                "label": item,
                "status": STATUS_LOADED,
                "poi_wave": 0,
            }
        )
    return out


def normalize_coverage_state(raw: dict[str, Any]) -> dict[str, Any]:
    state = dict(raw)
    regions_in = state.get("regions")
    regions: list[dict[str, Any]] = []
    if isinstance(regions_in, list):
        for item in regions_in:
            if not isinstance(item, dict):
                continue
            norm = _norm_region(item)
            if norm is not None:
                regions.append(norm)
    else:
        regions = _regions_from_legacy_loaded(state)
    state["regions"] = regions
    state["regions_loaded"] = [r["slug"] for r in regions if r["status"] == STATUS_LOADED]
    state["poi_count_db"] = _as_int(state.get("poi_count_db"), 0)
    state["poi_count_wave"] = _as_int(state.get("poi_count_wave"), 0)
    return state


def load_coverage_state(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return empty_coverage_state()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_coverage_state()
    if not isinstance(raw, dict):
        return empty_coverage_state()
    return normalize_coverage_state(raw)


def _loaded_slugs(regions: list[dict[str, Any]]) -> list[str]:
    return [r["slug"] for r in regions if r["status"] == STATUS_LOADED]


def merge_wave(
    state: dict[str, Any],
    wave_regions: list[dict[str, Any]],
    poi_count_db: int,
    poi_count_wave: int,
) -> dict[str, Any]:
    """Merge one wave into coverage state.

    Successful slugs become status=loaded. A failed wave never marks a region
    loaded and never drops a previously loaded region. poi_count_db is the
    caller COUNT from DB, not last-wave only.
    """
    base = normalize_coverage_state(state if isinstance(state, dict) else {})
    by_slug: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for reg in base["regions"]:
        slug = reg["slug"]
        if slug in by_slug:
            continue
        by_slug[slug] = dict(reg)
        order.append(slug)

    wave_n = _as_int(poi_count_wave, 0)
    for item in wave_regions:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label:
            label = slug
        wave_status = item.get("status")
        incoming_loaded = wave_status == STATUS_LOADED
        poi_wave = _as_int(item.get("poi_wave"), wave_n)
        prev = by_slug.get(slug)
        if prev is None:
            by_slug[slug] = {
                "slug": slug,
                "label": label,
                "status": STATUS_LOADED if incoming_loaded else STATUS_FAILED,
                "poi_wave": poi_wave,
            }
            order.append(slug)
            continue
        merged = dict(prev)
        merged["label"] = label
        if prev.get("status") == STATUS_LOADED:
            merged["status"] = STATUS_LOADED
            if incoming_loaded:
                merged["poi_wave"] = poi_wave
        else:
            merged["status"] = STATUS_LOADED if incoming_loaded else STATUS_FAILED
            merged["poi_wave"] = poi_wave
        by_slug[slug] = merged

    regions = [by_slug[s] for s in order]
    out = dict(base)
    out["regions"] = regions
    out["regions_loaded"] = _loaded_slugs(regions)
    out["poi_count_db"] = _as_int(poi_count_db, 0)
    out["poi_count_wave"] = wave_n
    return out


def save_coverage_state(path: Path | str, state: dict[str, Any]) -> None:
    p = Path(path)
    p.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
