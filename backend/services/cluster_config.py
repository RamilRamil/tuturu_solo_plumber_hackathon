"""Ranking weights and disc constants. Do not tune w1..w6 for pair #1 or top-5."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INGREDIENTS_PATH = REPO_ROOT / "ingredients.yaml"

ALLOWED_RADIUS_KM = frozenset({50, 100, 150})
DEFAULT_RADIUS_KM = 100
DEFAULT_LIMIT = 20
R_LOCAL_KM = 25.0
ANCIENT_YEAR = 1600

W1 = 1.0
W2 = 1.0
W3 = 1.0
W4 = 1.0
W5 = 1.0
W6 = 1.0


def load_ingredient_ids(path: Path = INGREDIENTS_PATH) -> set[str]:
    """Parse ingredient ids from ingredients.yaml without PyYAML."""
    ids: set[str] = set()
    in_ingredients = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ingredients:"):
            in_ingredients = True
            continue
        if not in_ingredients:
            continue
        stripped = line.strip()
        if stripped.startswith("- id:"):
            ids.add(stripped.split(":", 1)[1].strip())
    return ids
