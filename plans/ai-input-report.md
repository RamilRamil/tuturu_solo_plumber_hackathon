# AI-input report

Stream: AI input edge (`/api/parse` + IngredientMenu "Drugoe" field).
Worktree: `.worktrees/ai-input`
Branch: `codex/ai-input` from main `7854c30`.
Not merged. Not pushed. No parent `.env` edits.

Invariant: `knowledge/invariants/etalon-bypasses-llm.md` - etalon and
regression post `{ingredients}` to `/api/places`. LLM stays on the input
edge. Empty `OPENROUTER_API_KEY` does not block the product.

## G1 - router mounted

`backend/app.py` now imports `parse` and calls `app.include_router(parse.router)`
before places and price. `/healthz` and `/_sse_smoke` unchanged.

## G2 - OpenRouter, not Anthropic

`backend/services/parse_intent.py` `call_model`:

- URL `https://openrouter.ai/api/v1/chat/completions`
- `Authorization: Bearer {OPENROUTER_API_KEY}`
- body `{model, messages:[{role:system},{role:user}], temperature:0, max_tokens}`
- reply from `choices[0].message.content`
- default model `google/gemini-2.5-flash` (`BURGER_PARSE_MODEL` override)
- timeout 5s; any failure -> `None` -> existing `fallback()` HTTP 200
- empty key -> same fallback, never 500, no httpx call

Vocabulary still comes from `ingredients.yaml`. Output still goes through
places `PlacesIn` + `_validate`. No Tutu. No second ingredient list.

`backend/routers/parse.py` docstring/health mention `OPENROUTER_API_KEY`.

## G3 - frontend seam

`IngredientMenu.tsx` enables the existing "Drugoe" field (no second input,
chip grid / F3 collapse kept). Enter submits `POST /api/parse`.
On ingredients: SET selected chips; apply `radius_km` when it is 50/100/150.
Unmatched shown as `ne raspoznali: ...`. Network / timeout / empty ingredients:
silent fallback to chips. `fetchParse` in `frontend/src/api/client.ts` (live-only).

## Tests

`tests/test_parse.py` mocks `call_model` / `httpx`. No live network.

```
PYTHONPATH=. /Users/ramilmustafin/Projects/tuturu_hackaton/.venv/bin/python -m unittest tests.test_parse tests.test_places tests.test_guard -v
```

Etalon file `tests/test_places.py` still posts `{ingredients}` to `/api/places`
and does not import `parse` / `parse_intent`.

## Red zone (held)

- No LLM inside `/api/places` or `/api/price`
- No key required to start
- No output-pitch / streaming
- Did not change `cluster_places.py`, `price.py`, `tutu_mcp.py`, `schema.sql`,
  `api-contract.md`
