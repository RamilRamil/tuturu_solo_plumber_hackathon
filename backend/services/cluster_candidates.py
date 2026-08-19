"""Disc candidates: every hub, plus sellable-sellable pairs within radius_km."""

from __future__ import annotations

from typing import Any

from backend.services.cluster_geo import haversine_km

PROBE_SELLABLE = "sellable"


def iter_candidates(hubs: list[dict[str, Any]], radius_km: float) -> list[tuple[dict[str, Any], ...]]:
    """Single-hub sets for all hubs; pairs only among probe_status=sellable."""
    out: list[tuple[dict[str, Any], ...]] = []
    for hub in hubs:
        out.append((hub,))
    sellable = [h for h in hubs if h["probe_status"] == PROBE_SELLABLE]
    n = len(sellable)
    for i in range(n):
        for j in range(i + 1, n):
            a = sellable[i]
            b = sellable[j]
            dist = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            if dist <= radius_km:
                out.append((a, b))
    return out
