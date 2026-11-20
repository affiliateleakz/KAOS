"""KAOS Chart Snapshot: authenticated research-only screenshot interpretation
and archived price-structure matching. Screenshots are never persisted.
"""
import base64
import json
import os
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user
from db import db
from services_trading import get_entitlements
from kaos_chart_similarity import compare, PATTERN_TAGS
from kaos_candlestick_patterns import scan as scan_classic_patterns, catalog as classic_catalog

router = APIRouter(prefix="/api/v1/ai/chart-snapshot", tags=["chart-research"])
VALID_MARKET = re.compile(r"^[A-Z0-9_.-]{2,32}$")

async def permission(user=Depends(get_current_user)):
    ent = await get_entitlements(user)
    if not ent.get("aiInsights"):
        raise HTTPException(403, "Chart AI requires AI Insights entitlement")
    return user

class SnapshotInput(BaseModel):
    image_data: str = Field(min_length=100, max_length=2_000_000)
    symbol: str = Field(min_length=2, max_length=32)
    timeframe: str = Field(default="unknown", max_length=30)

@router.post("/analyze")
async def analyze(req: SnapshotInput, user=Depends(permission)):
    if not VALID_MARKET.fullmatch(req.symbol):
        raise HTTPException(422, "Invalid market symbol")
    if not req.image_data.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")):
        raise HTTPException(422, "Upload a PNG, JPEG, or WebP screenshot")
    encoded=req.image_data.partition(",")[2]
    try:
        image=base64.b64decode(encoded,validate=True)
    except Exception:
        raise HTTPException(422, "Invalid screenshot encoding")
    if len(image)>1_500_000 or len(image)<100:
        raise HTTPException(413, "Screenshot must be between 100 bytes and 1.5 MB")
    # Inspect actual file magic rather than trusting the declared data URL.
    if not (image.startswith(b"\x89PNG\r\n\x1a\n") or image.startswith(b"\xff\xd8\xff") or
            (image.startswith(b"RIFF") and image[8:12]==b"WEBP")):
        raise HTTPException(422, "Invalid image file signature")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Vision analysis unavailable until server OpenAI key is configured")
    prompt = (
        "You are KAOS Chart Research, an educational chart-image interpreter. "
        "Treat this screenshot as unverified visual information, not live prices. "
        "Never guess numerical confidence, price targets, asset identities or timeframes. "
        "Describe visible trend, candidate chart patterns, approximate qualitative support/resistance "
        "and both bullish and bearish scenarios. If text is unreadable state that. "
        "Do not tell the user to buy or sell or claim a winning trade. "
        "Choose one coarse visible structural pattern: uptrend, downtrend, range, "
        "breakout_up, breakout_down, or unknown. Choose unknown if the screenshot "
        "is too ambiguous. Pattern is an unvalidated visual classification. "
        f"User-supplied symbol: {req.symbol}; claimed timeframe: {req.timeframe}."
    )
    output_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type":"string", "enum":[*PATTERN_TAGS, "unknown"]},
            "analysis": {"type":"string"},
            "bullish_scenario": {"type":"string"},
            "bearish_scenario": {"type":"string"},
            "limitations": {"type":"string"}
        },
        "required": ["pattern","analysis","bullish_scenario","bearish_scenario","limitations"],
        "additionalProperties": False,
    }
    payload={"model":os.getenv("KAOS_CHART_VISION_MODEL","gpt-4.1-mini"),
             "input":[{"role":"user","content":[
                 {"type":"input_text","text":prompt},
                 {"type":"input_image","image_url":req.image_data}
             ]}],"max_output_tokens":650,
             "text":{"format":{"type":"json_schema","name":"kaos_chart_structure_v1",
                               "strict":True,"schema":output_schema}}}
    try:
        async with httpx.AsyncClient(timeout=35,follow_redirects=False) as client:
            response=await client.post("https://api.openai.com/v1/responses",
                headers={"Authorization":"Bearer "+key},json=payload)
        if response.status_code>=400:
            raise HTTPException(502,"Vision provider request failed")
        data=response.json()
        paragraphs=[p.get("text","") for item in data.get("output",[]) if item.get("type")=="message"
                    for p in item.get("content",[]) if p.get("type")=="output_text"]
        result="\n".join(paragraphs).strip()
        if not result:
            raise HTTPException(502,"No chart interpretation returned")
        try:
            structured=json.loads(result)
        except (ValueError, TypeError):
            raise HTTPException(502,"Vision provider returned invalid chart classification")
        if (not isinstance(structured,dict) or structured.get("pattern") not in (*PATTERN_TAGS,"unknown")
                or any(not isinstance(structured.get(k),str) for k in
                       ("analysis","bullish_scenario","bearish_scenario","limitations"))):
            raise HTTPException(502,"Vision provider chart classification is incomplete")
        return {"status":"visual_interpretation_only",
                "analysis":structured["analysis"][:2000],
                "pattern":structured["pattern"], "pattern_source":"vision_unverified",
                "bullish_scenario":structured["bullish_scenario"][:800],
                "bearish_scenario":structured["bearish_scenario"][:800],
                "limitations":structured["limitations"][:500],
                "model":payload["model"],"prediction":None,"confidence":None,
                "note":"Visual pattern label is unverified; historical analogs only compare coarse structure, not screenshot prices. No validated price forecast.",
                "image_stored":False}
    except httpx.HTTPError:
        raise HTTPException(502,"Vision provider temporarily unavailable")

@router.get("/similar")
async def similar(symbol:str, seconds:int=60, asset_class:str="crypto",
                  lookback:int=20, horizon:int=5, pattern:str|None=None,
                  user=Depends(permission)):
    if not VALID_MARKET.fullmatch(symbol) or asset_class not in ("crypto","stock","forex"):
        raise HTTPException(422,"Invalid symbol or asset class")
    if seconds not in (60,300,900) or not 10<=lookback<=60 or not 1<=horizon<=60:
        raise HTTPException(422,"Unsupported candle interval, lookback, or horizon")
    if pattern is not None and pattern not in PATTERN_TAGS:
        raise HTTPException(422,"Unsupported or uncertain screenshot pattern")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(5000)
    rows.reverse()
    if not rows:
        return {"count":0,"matches":[],"status":"unavailable","reason":"No archived market candles for this market"}
    # One feed only. Never combine heterogeneous providers into synthetic candles.
    source=rows[-1].get("source")
    rows=[r for r in rows if r.get("source")==source]
    try:
        result=compare(rows,lookback=lookback,horizon=horizon,pattern=pattern)
    except ValueError as e:
        raise HTTPException(422,str(e))
    return {**result,"symbol":symbol,"asset_class":asset_class,"seconds":seconds,
            "lookback_bars":lookback,"horizon_bars":horizon,
            "source":source,"archive_candles":len(rows),
            "note":"Historical pattern analogs, not a validated AI forecast or execution-ready signal."}


@router.get("/patterns/catalog")
async def patterns_catalog(user=Depends(permission)):
    """Show documented 50 names without pretending that all are implemented."""
    return {"research_only":True, "patterns":classic_catalog(),
            "note":"Heuristic detection is not a verified directional prediction."}


@router.get("/patterns/scan")
async def patterns_scan(symbol:str,seconds:int=60,asset_class:str="crypto",
                        user=Depends(permission)):
    if not VALID_MARKET.fullmatch(symbol) or asset_class not in ("crypto","stock","forex"):
        raise HTTPException(422,"Invalid market or asset class")
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported archived candle interval")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(300).to_list(300)
    rows.reverse()
    if not rows:
        return {"status":"unavailable","patterns":[],"reason":"No historical candles available",
                "research_only":True}
    source=rows[-1].get("source")
    rows=[r for r in rows if r.get("source")==source]
    interval_ms=seconds*1000
    # Do not run across missing bars; use only final contiguous segment.
    start=len(rows)-1
    while start>0 and rows[start]["ts"]-rows[start-1]["ts"]==interval_ms:
        start-=1
    segment=rows[start:]
    if len(segment)<5:
        return {"status":"unavailable","patterns":[],
                "reason":"Insufficient contiguous historical candles","research_only":True}
    try:
        matches=scan_classic_patterns(segment,max_patterns=40)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    decorated=[{**m, "end_ms":segment[m["index"]]["ts"]+interval_ms}
               for m in matches]
    chart_start=max(0,len(segment)-60)
    chart_bars=[{"ts":b["ts"],"open":b["open"],"high":b["high"],
                 "low":b["low"],"close":b["close"]} for b in segment[chart_start:]]
    visual_patterns=[{**m, "start_index":m["start_index"]-chart_start,
                      "index":m["index"]-chart_start}
                     for m in decorated if m["index"]>=chart_start
                     and m["start_index"]>=chart_start]
    return {"status":"research_only","patterns":decorated,
            "chart_bars":chart_bars,"visual_patterns":visual_patterns,
            "symbol":symbol,
            "seconds":seconds,"asset_class":asset_class,"source":source,
            "history_count":len(segment),
            "note":"Rules use completed candles. Pattern names do not imply predictive accuracy or trade authorization."}
