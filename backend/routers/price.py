"""Stream C: POST /api/price SSE."""

from __future__ import annotations

import asyncio
import json
import queue
import re
import threading
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.price import (
    EVENT_PAUSE_S,
    FIRST_LEG_PAUSE_S,
    UnknownCluster,
    demo_pace_enabled,
    iter_price_events,
    load_cluster_row,
    open_mcp,
)
from lib.tutu_mcp import TutuMcp, check_resolve, price_is_absent

_ = TutuMcp, check_resolve, price_is_absent

router = APIRouter()
_MONTH_RE = re.compile(r"^[0-9]{4}-[0-9]{2}$")

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


class PriceRequest(BaseModel):
    cluster_id: str
    origin: str
    days: int = Field(ge=1)
    month: str
    adults: int = Field(default=1, ge=1)
    children_ages: list[int] = Field(default_factory=list)
    budget_scope: Literal["transport", "all"] = "transport"


def sse_frame(name: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return "event: " + name + "\ndata: " + data + "\n\n"


def _load_cluster_or_404(cluster_id: str) -> None:
    mcp = open_mcp()
    try:
        load_cluster_row(mcp.conn, cluster_id)
    except UnknownCluster:
        raise HTTPException(status_code=404, detail="cluster not found") from None
    finally:
        mcp.close()


async def _disconnected(request: Request) -> bool:
    return await request.is_disconnected()


@router.post("/api/price")
async def post_price(body: PriceRequest, request: Request) -> StreamingResponse:
    if not _MONTH_RE.match(body.month):
        raise HTTPException(status_code=400, detail="invalid month")
    _load_cluster_or_404(body.cluster_id)

    req = body.model_dump()
    demo = demo_pace_enabled()

    async def gen():
        events_q: queue.Queue = queue.Queue()
        cancel = threading.Event()

        def produce() -> None:
            mcp = open_mcp()
            try:
                for name, payload in iter_price_events(req, mcp, cancel=cancel):
                    if cancel.is_set():
                        break
                    events_q.put(("ok", name, payload))
            except Exception as exc:
                events_q.put(("err", exc, None))
            finally:
                mcp.close()
                events_q.put(("end", None, None))

        worker = threading.Thread(target=produce, name="price-sse", daemon=True)
        worker.start()
        first_event = True
        first_leg = True
        try:
            while True:
                if await _disconnected(request):
                    cancel.set()
                    break
                kind, a, b = await asyncio.to_thread(events_q.get)
                if kind == "end":
                    break
                if kind == "err":
                    raise a
                name, payload = a, b
                if demo:
                    if name == "leg" and first_leg:
                        if FIRST_LEG_PAUSE_S > 0:
                            await asyncio.sleep(FIRST_LEG_PAUSE_S)
                        first_leg = False
                    elif not first_event:
                        if EVENT_PAUSE_S > 0:
                            await asyncio.sleep(EVENT_PAUSE_S)
                first_event = False
                yield sse_frame(name, payload)
                if await _disconnected(request):
                    cancel.set()
                    break
        finally:
            cancel.set()
            await asyncio.to_thread(worker.join, 60.0)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
