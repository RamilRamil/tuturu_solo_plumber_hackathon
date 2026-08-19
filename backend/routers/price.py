"""Stream C: POST /api/price SSE."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.price import (
    EVENT_PAUSE_S,
    FIRST_LEG_PAUSE_S,
    UnknownCluster,
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


@router.post("/api/price")
async def post_price(body: PriceRequest) -> StreamingResponse:
    if not _MONTH_RE.match(body.month):
        raise HTTPException(status_code=400, detail="invalid month")
    mcp = open_mcp()
    try:
        load_cluster_row(mcp.conn, body.cluster_id)
    except UnknownCluster:
        mcp.close()
        raise HTTPException(status_code=404, detail="cluster not found") from None

    req = body.model_dump()

    async def gen():
        first_event = True
        first_leg = True
        try:
            for name, payload in iter_price_events(req, mcp):
                if name == "leg" and first_leg:
                    if FIRST_LEG_PAUSE_S > 0:
                        await asyncio.sleep(FIRST_LEG_PAUSE_S)
                    first_leg = False
                elif not first_event:
                    if EVENT_PAUSE_S > 0:
                        await asyncio.sleep(EVENT_PAUSE_S)
                first_event = False
                yield sse_frame(name, payload)
        finally:
            mcp.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
