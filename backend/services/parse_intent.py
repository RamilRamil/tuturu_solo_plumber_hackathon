"""Free-text -> burger ingredients. Edge layer only: no Tutu, no core logic.

Invariant (knowledge/invariants/etalon-bypasses-llm.md): this module is an
optional convenience on the input edge. The etalon and every regression test
feed {ingredients} straight into /api/places and never touch this code path.

Single source of truth for the vocabulary is ingredients.yaml. This module
builds the model prompt from that file and validates the model output with the
very same guard that manual input goes through (routers.places._validate).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException

from backend.services.cluster_config import (
    ALLOWED_RADIUS_KM,
    DEFAULT_RADIUS_KM,
    INGREDIENTS_PATH,
    load_ingredient_ids,
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"
TIMEOUT_S = 5.0
MAX_TOKENS = 400
MAX_TEXT_CHARS = 600

NEAR_RADIUS_KM = 50


# ---------------------------------------------------------------- vocabulary

def load_catalog(path: Path = INGREDIENTS_PATH) -> list[dict[str, str]]:
    """Read id / name_ru / group (+ group name_ru) out of ingredients.yaml.

    No second list lives in Python: the ids are cross-checked against
    load_ingredient_ids(), the same set /api/places validates against.
    """
    groups: dict[str, str] = {}
    items: list[dict[str, str]] = []
    section = ""
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("groups:"):
            section = "groups"
            current = None
            continue
        if line.startswith("ingredients:"):
            section = "ingredients"
            current = None
            continue
        if not section:
            continue
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current = {"id": stripped.split(":", 1)[1].strip()}
            if section == "groups":
                groups[current["id"]] = ""
            else:
                items.append(current)
            continue
        if current is None:
            continue
        if stripped.startswith("name_ru:"):
            value = stripped.split(":", 1)[1].strip()
            if section == "groups":
                groups[current["id"]] = value
            else:
                current["name_ru"] = value
        elif stripped.startswith("group:") and section == "ingredients":
            current["group"] = stripped.split(":", 1)[1].strip()

    known = load_ingredient_ids(path)
    catalog: list[dict[str, str]] = []
    for item in items:
        if item["id"] not in known:
            continue
        catalog.append(
            {
                "id": item["id"],
                "name_ru": item.get("name_ru", item["id"]),
                "group": item.get("group", ""),
                "group_name_ru": groups.get(item.get("group", ""), ""),
            }
        )
    return catalog


def build_system_prompt(catalog: list[dict[str, str]] | None = None) -> str:
    catalog = catalog if catalog is not None else load_catalog()
    lines: list[str] = []
    last_group = None
    for item in catalog:
        if item["group"] != last_group:
            last_group = item["group"]
            lines.append(f"# {item['group_name_ru'] or item['group']}")
        lines.append(f"- {item['id']} - {item['name_ru']}")
    vocabulary = "\n".join(lines)
    allowed = ", ".join(str(r) for r in sorted(ALLOWED_RADIUS_KM))
    return (
        "Ты раскладываешь свободную фразу о путешествии на ингредиенты «бургера» -\n"
        "фиксированный словарь категорий мест. Отвечай ТОЛЬКО JSON-объектом, без\n"
        "пояснений и без markdown-ограды.\n\n"
        "Формат ответа:\n"
        '{"ingredients": ["<id>", ...], "radius_hint": <число или null>}\n\n'
        "Правила:\n"
        "- В ingredients клади ТОЛЬКО id из словаря ниже. Ничего не выдумывай.\n"
        "- Если во фразе нет ничего подходящего - верни пустой список.\n"
        "- Не добавляй ингредиенты «на всякий случай»: только то, что прямо следует из фразы.\n"
        f"- radius_hint - одно из: {allowed}, либо null.\n"
        f"  «недалеко», «рядом», «близко», «на один день» -> {NEAR_RADIUS_KM}.\n"
        "  «подальше», «не жалко ехать», «далеко» -> 150. Иначе null.\n\n"
        "Словарь ингредиентов:\n"
        f"{vocabulary}\n"
    )


# ------------------------------------------------------------------- guard

def _validated(candidates: list[str], radius_km: int) -> tuple[list[str], list[str]]:
    """Run every candidate through the same guard manual input goes through."""
    from backend.routers.places import PlacesIn, _validate

    ingredients: list[str] = []
    unmatched: list[str] = []
    for raw in candidates:
        item = raw.strip() if isinstance(raw, str) else ""
        if not item:
            unmatched.append(str(raw))
            continue
        if item in ingredients:
            continue
        try:
            _validate(PlacesIn(ingredients=[item], radius_km=radius_km))
        except HTTPException:
            unmatched.append(item)
            continue
        ingredients.append(item)
    return ingredients, unmatched


def pick_radius(requested: Any, hint: Any) -> int:
    for value in (requested, hint):
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value in ALLOWED_RADIUS_KM:
            return value
    return DEFAULT_RADIUS_KM


# -------------------------------------------------------------------- model

def _api_key() -> str:
    return (os.environ.get("OPENROUTER_API_KEY") or "").strip()


def _model() -> str:
    override = (os.environ.get("BURGER_PARSE_MODEL") or "").strip()
    return override or DEFAULT_MODEL


def call_model(text: str, system_prompt: str) -> str | None:
    """POST to OpenRouter chat/completions. Any failure returns None."""
    key = _api_key()
    if not key:
        return None
    payload = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:MAX_TEXT_CHARS]},
        ],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }
    headers = {
        "Authorization": "Bearer " + key,
        "content-type": "application/json",
    }
    try:
        res = httpx.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT_S)
        if res.status_code != 200:
            return None
        body = res.json()
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    joined = content.strip()
    return joined or None


def extract_json(raw: str | None) -> dict[str, Any] | None:
    """Defensive parse: fenced blocks, stray prose, non-objects -> None."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


# ------------------------------------------------------------------ service

def fallback(text: str, radius_km: Any = None) -> dict[str, Any]:
    """No key / dead model / garbage answer: honest, deterministic, no 500."""
    stripped = (text or "").strip()
    return {
        "ingredients": [],
        "radius_km": pick_radius(radius_km, None),
        "unmatched": [stripped] if stripped else [],
    }


def parse_intent(text: str, radius_km: Any = None) -> dict[str, Any]:
    stripped = (text or "").strip()
    if not stripped:
        return fallback("", radius_km)
    data = extract_json(call_model(stripped, build_system_prompt()))
    if data is None:
        return fallback(stripped, radius_km)
    raw_items = data.get("ingredients")
    if not isinstance(raw_items, list):
        return fallback(stripped, radius_km)
    chosen = pick_radius(radius_km, data.get("radius_hint"))
    ingredients, unmatched = _validated(raw_items, chosen)
    if not ingredients and not unmatched:
        unmatched = [stripped]
    return {"ingredients": ingredients, "radius_km": chosen, "unmatched": unmatched}
