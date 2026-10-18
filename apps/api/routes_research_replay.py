"""Authenticated, bounded historical replay endpoint; never submits orders."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user
from kaos_trend_pause_replay import replay

router = APIRouter(prefix="/api/v1/research", tags=["research"])

class Candle(BaseModel):
    ts: int
    open: float
    high: float
    low: float
    close: float

class ReplayRequest(BaseModel):
    minute_candles: list[Candle] = Field(min_length=53, max_length=6000)
    fifteen_second_candles: list[Candle] = Field(min_length=24, max_length=24000)
    horizon_seconds: int = Field(default=60, ge=15, le=3600, multiple_of=15)

@router.post("/trend-pause/replay")
async def trend_pause_replay(req: ReplayRequest, user: dict = Depends(get_current_user)):
    try:
        result = replay([c.model_dump() for c in req.minute_candles],
                        [c.model_dump() for c in req.fifteen_second_candles],
                        horizon_seconds=req.horizon_seconds)
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"strategy": "KAOS_TREND_PAUSE_V1", "research_only": True,
            "execution_enabled": False, **result}
