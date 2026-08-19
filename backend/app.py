"""Hour-0 FastAPI process: SSE smoke only. Product /api/places and /api/price are Worker B/C."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="burger-backend", version="0.0.1")
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
