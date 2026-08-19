"""Lexicographic coverage then cluster_score. Rarity is an honest combo count."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from backend.services.cluster_config import W1, W2, W3, W4, W5, W6


def _combo_key(matched: list[str]) -> tuple[str, ...]:
    return tuple(sorted(matched))


def cluster_score(
    *,
    coverage_ratio: float,
    sum_significance: float,
    rarity: float,
    population: float,
    diameter_km: float,
    radius_km: float,
    on_foot: int,
) -> float:
    compact = diameter_km / radius_km if radius_km else 0.0
    return (
        W1 * coverage_ratio
        + W2 * math.log(1.0 + sum_significance)
        + W3 * rarity
        + W4 * math.log(1.0 + population)
        - W5 * compact
        - W6 * float(on_foot)
    )


def rank_places(
    places: list[dict[str, Any]],
    ingredients: list[str],
    radius_km: int,
) -> list[dict[str, Any]]:
    n_ing = max(len(ingredients), 1)
    combo_n: dict[tuple[str, ...], int] = defaultdict(int)
    for place in places:
        combo_n[_combo_key(place["coverage"]["matched"])] += 1

    scored: list[dict[str, Any]] = []
    for place in places:
        matched = place["coverage"]["matched"]
        key = _combo_key(matched)
        total = combo_n[key]
        rarity = 1.0 / total if total else 0.0
        coverage_ratio = len(matched) / n_ing
        score = cluster_score(
            coverage_ratio=coverage_ratio,
            sum_significance=float(place.get("sum_significance") or 0.0),
            rarity=rarity,
            population=float(place.get("population") or 0.0),
            diameter_km=float(place.get("diameter_km") or 0.0),
            radius_km=float(radius_km),
            on_foot=int(place.get("on_foot") or 0),
        )
        card = {
            "cluster_id": place["cluster_id"],
            "title": place["title"],
            "hubs": place["hubs"],
            "center": place["center"],
            "diameter_km": place["diameter_km"],
            "coverage": place["coverage"],
            "objects": place["objects"],
            "_score": score,
            "_combo": key,
            "_combo_total": total,
        }
        scored.append(card)

    scored.sort(key=lambda c: (-len(c["coverage"]["matched"]), -c["_score"]))

    rank_in_combo: dict[tuple[str, ...], int] = defaultdict(int)
    out: list[dict[str, Any]] = []
    for card in scored:
        key = card["_combo"]
        rank_in_combo[key] += 1
        out.append(
            {
                "cluster_id": card["cluster_id"],
                "title": card["title"],
                "hubs": card["hubs"],
                "center": card["center"],
                "diameter_km": card["diameter_km"],
                "coverage": card["coverage"],
                "rarity": {
                    "rank": rank_in_combo[key],
                    "total_places_with_combo": card["_combo_total"],
                },
                "objects": card["objects"],
            }
        )
    return out
