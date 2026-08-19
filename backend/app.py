"""Hour-0 FastAPI process: SSE smoke + empty B/C routers.

Product handlers live in backend/routers/places.py (B) and
backend/routers/price.py (C). This file is architect-owned: streams do not
edit it.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from backend.routers import parse, places, price

app = FastAPI(title="burger-backend", version="0.0.1")
app.include_router(parse.router)
app.include_router(places.router)
app.include_router(price.router)
SMOKE_PAUSE_S = 1.0


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    db = Path(os.environ.get("BURGER_DB") or "data/burger.db")
    seed = _truthy("BURGER_SEED_FIXTURES")
    data_mode = "fixtures" if seed or db.name.endswith("g10.db") else "live-data"
    size = db.stat().st_size if db.is_file() else 0
    return {
        "ok": True,
        "db_path": str(db),
        "db_bytes": size,
        "data_mode": data_mode,
        "live_tutu": _truthy("BURGER_LIVE_TUTU"),
        "sc_price_accepted": _truthy("BURGER_SC_PRICE_ACCEPTED"),
    }


@app.get("/_sse_smoke")
async def sse_smoke() -> StreamingResponse:
    async def gen():
        for n in range(3):
            payload = json.dumps({"n": n}, ensure_ascii=True)
            yield "event: ping\ndata: " + payload + "\n\n"
            if n < 2:
                await asyncio.sleep(SMOKE_PAUSE_S)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=headers,
    )
