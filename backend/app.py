"""Hour-0 FastAPI process: SSE smoke + empty B/C routers.

Product handlers live in backend/routers/places.py (B) and
backend/routers/price.py (C). This file is architect-owned: streams do not
edit it.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from backend.routers import places, price

app = FastAPI(title="burger-backend", version="0.0.1")
app.include_router(places.router)
app.include_router(price.router)
SMOKE_PAUSE_S = 1.0


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


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
