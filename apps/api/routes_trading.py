"""KAOS trading pipeline: intelligence delivery + execution state machine + telemetry.

Core priority path (extension consumes /api/v1/trading/*):
  intelligence -> signal -> order attempt -> broker confirmed -> trade open -> result
Broker confirmation is authoritative. Idempotent so retries never duplicate trade records.
"""
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Request

from db import db, new_id, now_iso, clean
from auth import get_current_user, require_role
from services import compute_license, get_setting, set_setting, audit_log
from services_trading import AI_EXECUTION_MODES, AI_EXECUTION_SETTING
from services_trading import (get_official_strategy, get_trading_config, get_entitlements,
                              kaos_strategy_predict, kaos_ai_predict, telemetry_summary,
                              TRADING_MODES)

v1t = APIRouter(prefix="/api/v1/trading", tags=["trading-v1"])
mt = APIRouter(prefix="/api/trading", tags=["trading-member"])
at = APIRouter(prefix="/api/admin", tags=["trading-admin"])
share = APIRouter(tags=["share"])


# ----- request models -----
class IntelReq(BaseModel):
    asset: str
    platform: str = "pocket_option"
    mode: str = "STRATEGY"
    chartSlot: Optional[int] = None
    bucket: Optional[str] = None
    context: dict = {}


class SignalRecordReq(BaseModel):
    clientSignalId: Optional[str] = None
    asset: str
    platform: str = "pocket_option"
    mode: str = "STRATEGY"
    chartSlot: Optional[int] = None
    direction: str
    engine: Optional[str] = None
    requestedAmount: float = 1.0
    requestedExpiration: str = "30s"
    strategyPrediction: Optional[dict] = None
    aiPrediction: Optional[dict] = None
    signalTimestamp: Optional[str] = None


class ExecAttemptReq(BaseModel):
    signalId: str
    executionAttemptId: str  # client-generated; unique -> idempotent
    platform: str = "pocket_option"
    chartSlot: Optional[int] = None
    asset: str
    direction: str
    requestedAmount: float
    requestedExpiration: str
    submissionTimestamp: Optional[str] = None


class ConfirmReq(BaseModel):
    brokerOrderId: Optional[str] = None
    entryPrice: Optional[float] = None
    brokerConfirmedTimestamp: Optional[str] = None


class ResultReq(BaseModel):
    result: str  # WIN | LOSS | TIE
    pnl: float = 0.0
    exitPrice: Optional[float] = None
    resultTimestamp: Optional[str] = None


class FailReq(BaseModel):
    failureCode: str
    failureReason: Optional[str] = ""


async def _require_authorized(request: Request, user: dict, broker: str = "pocket_option"):
    """Trading endpoints require a live, server-authorized license + registered device."""
    did = request.headers.get("X-Device-Id")
    if not did or not did.strip():
        raise HTTPException(status_code=403, detail="Registered device required")
    device = await db.devices.find_one({"installId": did, "userId": user["id"]})
    if not device or device.get("revoked"):
        raise HTTPException(status_code=403, detail="Device not authorized")
    lic = await compute_license(user, device, broker)
    if not lic["authorized"]:
        raise HTTPException(status_code=403, detail={"error": "not_authorized", "license": lic})
    return lic, (device or {})


async def _check_mode(user, mode):
    ent = await get_entitlements(user)
    if not ent.get("botAccess"):
        raise HTTPException(status_code=403, detail="Bot access not included in your plan")
    if mode not in TRADING_MODES:
        raise HTTPException(status_code=400, detail="Invalid trading mode")
    if mode in AI_EXECUTION_MODES and ent.get("aiExecutionLocked"):
        raise HTTPException(status_code=403, detail="AI-controlled trading is locked until independently validated")
    if mode not in (ent.get("modes") or []):
        raise HTTPException(status_code=403, detail=f"Mode {mode} not entitled by your plan")
    return ent


def chart_limit_error(ent: dict, slot) -> Optional[dict]:
    """0-based chart slot must be below the plan's chartLimit (Free 1, Pro 4, Ultimate 4)."""
    if slot is None:
        return None
    limit = int(ent.get("chartLimit") or 1)
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0 or slot >= limit:
        return {"error": "chart_limit", "chartLimit": limit,
                "message": f"Your plan allows {limit} active trading chart{'s' if limit != 1 else ''}."}
    return None


async def _check_chart(user, slot):
    err = chart_limit_error(await get_entitlements(user), slot)
    if err:
        raise HTTPException(status_code=403, detail=err)


# ----- config the extension pulls -----
@v1t.get("/config")
async def trading_config(user: dict = Depends(get_current_user)):
    ent = await get_entitlements(user)
    return {
        "entitlements": ent,
        "officialStrategy": await get_official_strategy(),
        "tradingConfig": await get_trading_config(),
        "modes": TRADING_MODES,
        "userMode": user.get("trading_mode", "STRATEGY"),
    }


# ----- intelligence: STRATEGY / AI / both (shown separately) -----
@v1t.post("/intelligence")
async def intelligence(req: IntelReq, request: Request, user: dict = Depends(get_current_user)):
    await _require_authorized(request, user, req.platform)
    await _check_mode(user, req.mode)
    await _check_chart(user, req.chartSlot)
    ctx = {"bucket": req.bucket or "", **(req.context or {})}
    strat = await kaos_strategy_predict(req.asset, req.platform, ctx) if req.mode in ("STRATEGY", "STRATEGY_AI") else None
    ai = await kaos_ai_predict(req.asset, req.platform, ctx, user=user) if req.mode in ("AI", "STRATEGY_AI") else None
    tc = await get_trading_config()
    authority = req.mode if req.mode != "STRATEGY_AI" else tc.get("executionAuthority", "STRATEGY")
    chosen = strat if authority in ("STRATEGY", "STRATEGY_AI") and strat else ai
    sig = {
        "id": new_id("sig"), "userId": user["id"], "asset": req.asset, "platform": req.platform,
        "tradingMode": req.mode, "engine": (chosen or {}).get("engine"),
        "direction": (chosen or {}).get("direction"), "expiration": (chosen or {}).get("expiration"),
        "strategyPrediction": strat, "aiPrediction": ai, "executionAuthority": authority,
        "state": "SIGNAL_DELIVERED", "simulated": True, "createdAt": now_iso(),
    }
    await db.signals.insert_one(dict(sig))
    return {**clean(sig), "note": "SIMULATED intelligence (placeholder). Real KAOS Strategy/AI integrate later."}


# ----- record a signal the extension generated locally -----
@v1t.post("/signal")
async def record_signal(req: SignalRecordReq, request: Request, user: dict = Depends(get_current_user)):
    await _require_authorized(request, user, req.platform)
    await _check_mode(user, req.mode)
    await _check_chart(user, req.chartSlot)
    if req.clientSignalId:
        existing = await db.signals.find_one({"clientSignalId": req.clientSignalId, "userId": user["id"]})
        if existing:
            return {"signalId": existing["id"], "duplicate": True}
    sig = {
        "id": new_id("sig"), "clientSignalId": req.clientSignalId, "userId": user["id"],
        "asset": req.asset, "platform": req.platform, "tradingMode": req.mode,
        "direction": req.direction, "engine": req.engine, "expiration": req.requestedExpiration,
        "requestedAmount": req.requestedAmount, "strategyPrediction": req.strategyPrediction,
        "aiPrediction": req.aiPrediction, "signalTimestamp": req.signalTimestamp,
        "state": "SIGNAL_GENERATED", "createdAt": now_iso(),
    }
    await db.signals.insert_one(dict(sig))
    return {"signalId": sig["id"], "duplicate": False}


# ----- ORDER_SUBMIT_ATTEMPT (idempotent on executionAttemptId) -----
@v1t.post("/execution")
async def order_attempt(req: ExecAttemptReq, request: Request, user: dict = Depends(get_current_user)):
    lic, device = await _require_authorized(request, user, req.platform)
    await _check_chart(user, req.chartSlot)
    existing = await db.trades.find_one({"executionAttemptId": req.executionAttemptId, "userId": user["id"]})
    if existing:
        return {"tradeId": existing["id"], "state": existing["state"], "idempotent": True}
    sig = await db.signals.find_one({"id": req.signalId, "userId": user["id"]})
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    if sig.get("simulated") or req.platform == "coinbase":
        raise HTTPException(status_code=403, detail="Use verified Coinbase execution route; simulated or Coinbase telemetry cannot create live trades")
    if req.platform != sig.get("platform") or req.asset != sig.get("asset") or req.direction != sig.get("direction"):
        raise HTTPException(status_code=422, detail="Execution does not match owned signal")
    tc = await get_trading_config()
    trade = {
        "id": new_id("trade"), "executionAttemptId": req.executionAttemptId,
        "signalId": req.signalId, "userId": user["id"], "deviceId": device.get("id"),
        "licenseId": user.get("license_id"), "platform": req.platform, "asset": req.asset,
        "direction": req.direction, "tradingMode": (sig or {}).get("tradingMode"),
        "engine": (sig or {}).get("engine"),
        "strategyVersion": ((sig or {}).get("strategyPrediction") or {}).get("strategyVersion"),
        "aiModelVersion": ((sig or {}).get("aiPrediction") or {}).get("modelVersion") or tc.get("aiModelVersion"),
        "requestedAmount": req.requestedAmount, "requestedExpiration": req.requestedExpiration,
        "signalTimestamp": (sig or {}).get("signalTimestamp") or (sig or {}).get("createdAt"),
        "submissionTimestamp": req.submissionTimestamp or now_iso(),
        "brokerConfirmedTimestamp": None, "entryPrice": None, "exitPrice": None,
        "resultTimestamp": None, "result": None, "pnl": None,
        "failureCode": None, "failureReason": None, "brokerOrderId": None,
        "state": "ORDER_SUBMIT_ATTEMPT", "simulated": (sig or {}).get("simulated", False),
        "createdAt": now_iso(), "updatedAt": now_iso(),
    }
    await db.trades.insert_one(dict(trade))
    await db.signals.update_one({"id": req.signalId}, {"$set": {"state": "ORDER_SUBMIT_ATTEMPT"}})
    return {"tradeId": trade["id"], "state": trade["state"], "idempotent": False}


async def _get_trade(tid, user):
    t = await db.trades.find_one({"id": tid, "userId": user["id"]})
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found")
    return t


@v1t.post("/execution/{tid}/confirm")
async def broker_confirm(tid: str, req: ConfirmReq, request: Request, user: dict = Depends(get_current_user)):
    await _require_authorized(request, user)
    t = await _get_trade(tid, user)
    if t.get("platform") == "coinbase":
        raise HTTPException(status_code=403, detail="Coinbase confirmations must come from verified exchange fills")
    if t["state"] in ("BROKER_CONFIRMED", "TRADE_OPEN", "TRADE_RESULT"):
        return {"tradeId": tid, "state": t["state"], "idempotent": True}
    if t["state"] == "ORDER_FAILED":
        raise HTTPException(status_code=409, detail="Trade already failed")
    # Broker confirmation opens the position: record the broker fill and advance to TRADE_OPEN
    # (state machine: ORDER_SUBMIT_ATTEMPT -> BROKER_CONFIRMED -> TRADE_OPEN). `brokerConfirmed`
    # is persisted so a broker-confirmed trade can never be mistaken for a failure/loss.
    await db.trades.update_one({"id": tid}, {"$set": {
        "state": "TRADE_OPEN", "brokerConfirmed": True, "brokerOrderId": req.brokerOrderId,
        "entryPrice": req.entryPrice,
        "brokerConfirmedTimestamp": req.brokerConfirmedTimestamp or now_iso(), "updatedAt": now_iso()}})
    return {"tradeId": tid, "state": "TRADE_OPEN"}


@v1t.post("/execution/{tid}/result")
async def trade_result(tid: str, req: ResultReq, request: Request, user: dict = Depends(get_current_user)):
    await _require_authorized(request, user)
    t = await _get_trade(tid, user)
    if t.get("platform") == "coinbase":
        raise HTTPException(status_code=403, detail="Coinbase results must come from verified exit fills")
    if req.result not in ("WIN", "LOSS", "TIE"):
        raise HTTPException(status_code=400, detail="Invalid result")
    # idempotent: a resolved trade returns its recorded result without erroring
    if t.get("result"):
        return {"tradeId": tid, "state": "TRADE_RESULT", "idempotent": True}
    # only a broker-confirmed trade can produce a real result
    if t["state"] not in ("TRADE_OPEN", "BROKER_CONFIRMED"):
        raise HTTPException(status_code=409, detail=f"Cannot record result from state {t['state']}")
    await db.trades.update_one({"id": tid}, {"$set": {
        "state": "TRADE_RESULT", "result": req.result, "pnl": req.pnl, "exitPrice": req.exitPrice,
        "resultTimestamp": req.resultTimestamp or now_iso(), "updatedAt": now_iso()}})
    return {"tradeId": tid, "state": "TRADE_RESULT", "result": req.result}


@v1t.post("/execution/{tid}/fail")
async def order_failed(tid: str, req: FailReq, request: Request, user: dict = Depends(get_current_user)):
    await _require_authorized(request, user)
    t = await _get_trade(tid, user)
    # A broker-confirmed / open / resolved order must never be masked as failed.
    if t["state"] != "ORDER_SUBMIT_ATTEMPT":
        raise HTTPException(status_code=409, detail=f"Cannot fail from state {t['state']}")
    await db.trades.update_one({"id": tid}, {"$set": {
        "state": "ORDER_FAILED", "failureCode": req.failureCode, "failureReason": req.failureReason,
        "updatedAt": now_iso()}})
    return {"tradeId": tid, "state": "ORDER_FAILED"}


# ----- member trading surfaces -----
@mt.get("/overview")
async def trading_overview(user: dict = Depends(get_current_user)):
    ent = await get_entitlements(user)
    signals = await db.signals.find({"userId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(15)
    trades = await db.trades.find({"userId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(25)
    summary = await telemetry_summary({"userId": user["id"]})
    return {"entitlements": ent, "mode": user.get("trading_mode", "STRATEGY"),
            "officialStrategy": await get_official_strategy(), "modes": TRADING_MODES,
            "recentSignals": signals, "recentTrades": trades, "summary": summary}


class BacktestReq(BaseModel):
    candles: list
    asset: str = "EURUSD"


@mt.post("/backtest")
async def backtest(req: BacktestReq, user: dict = Depends(get_current_user)):
    """Bounded strict replay of the same engine as the extension; no training or orders."""
    if not (await get_entitlements(user)).get("botAccess"):
        raise HTTPException(403,"Bot access required")
    import asyncio
    from signature_backtest import replay
    if len(req.candles)<100:raise HTTPException(400,"Provide at least 100 aligned five-second candles with timestamps")
    try:report=await asyncio.to_thread(replay,{req.asset:req.candles[-2500:]},provenance="User-supplied candles; fills unverified")
    except (ValueError,KeyError,TypeError) as exc:raise HTTPException(422,str(exc))
    by={};equity=[];net=0
    for trade in report['trades']:
        row=by.setdefault(trade['engine'],dict(trades=0,wins=0,losses=0,ties=0))
        row['trades']+=1;row[{'WIN':'wins','LOSS':'losses','TIE':'ties'}[trade['result']]]+=1
        net+=trade['unit_pnl'];equity.append(round(net,4))
    for row in by.values():row['winRate']=round(100*row['wins']/max(1,row['wins']+row['losses']),2)
    full=report['full'];overall={k:full[k] for k in ('trades','wins','losses','ties')}
    overall['winRate']=round(100*full['win_rate'],2) if full['win_rate'] is not None else None
    return {"bars":report['candles'],"byEngine":by,"overall":overall,"equity":equity[-240:],"strategyVersion":report['version'],"simulated":False,"mode":"offline-research-only","holdout":report['holdout'],"limitations":report['limitations'],"researchGate":report['research_gate'],"liveApproved":False}


class ModeReq(BaseModel):
    mode: str


class ShareReq(BaseModel):
    engine: str
    direction: str
    expiration: str
    confidence: float
    reason: Optional[str] = ""
    strategyVersion: Optional[str] = None
    asset: str = "EURUSD"
    candles: list = []
    triggerPos: Optional[int] = None


@mt.post("/share")
async def create_share(req: ShareReq, user: dict = Depends(get_current_user)):
    """Persist a shareable KAOS signal card (read-only snapshot). Returns a public share id/url,
    embedding the sharer's affiliate code so sign-ups from the card credit their commissions."""
    win = (req.candles or [])[-60:]
    acc = await db.affiliate_accounts.find_one({"userId": user["id"], "status": "active"}, {"_id": 0, "code": 1})
    ref = acc["code"] if acc else None
    doc = {"id": new_id("shr"), "userId": user["id"], "engine": req.engine, "direction": req.direction,
           "expiration": req.expiration, "confidence": req.confidence, "reason": req.reason,
           "strategyVersion": req.strategyVersion, "asset": req.asset, "candles": win,
           "triggerPos": req.triggerPos, "sharerRef": ref, "createdAt": now_iso()}
    await db.signal_shares.insert_one(dict(doc))
    qs = f"?ref={ref}" if ref else ""
    return {"id": doc["id"], "path": f"/s/{doc['id']}{qs}", "ogPath": f"/api/s/{doc['id']}{qs}", "refCode": ref}


@share.get("/api/share/{sid}")
async def get_share(sid: str):
    doc = await db.signal_shares.find_one({"id": sid}, {"_id": 0, "userId": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Share not found")
    return doc


def _render_share_png(doc: dict) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    import io
    W, Hc = 1200, 630
    img = Image.new("RGB", (W, Hc), (11, 11, 11))
    dr = ImageDraw.Draw(img)
    gold, grey, white, green, red = (212, 175, 55), (138, 138, 138), (255, 255, 255), (34, 197, 94), (198, 40, 40)

    def font(sz):
        try:
            return ImageFont.load_default(size=sz)
        except Exception:
            return ImageFont.load_default()

    dr.rectangle([14, 14, W - 14, Hc - 14], outline=gold, width=3)
    dr.text((60, 48), "KAOS TRADING", font=font(52), fill=gold)
    dr.text((62, 112), "TRADE WITH KAOS", font=font(22), fill=grey)
    dr.text((60, 176), str(doc.get("engine", "")), font=font(78), fill=white)
    dr.text((60, 268), str(doc.get("direction", "")), font=font(54),
            fill=green if doc.get("direction") == "BUY" else red)
    meta = f"expiry {doc.get('expiration')}   confidence {doc.get('confidence')}   v{doc.get('strategyVersion')}"
    dr.text((62, 336), meta, font=font(24), fill=(207, 207, 207))
    win = doc.get("candles") or []
    tp = doc.get("triggerPos")
    if win:
        x0, y0, cH, n = 60, 400, 180, len(win)
        cw = (W - 120) / n
        hi = max(c["high"] for c in win)
        lo = min(c["low"] for c in win)
        rng = max(1e-9, hi - lo)

        def yy(v):
            return y0 + cH - ((v - lo) / rng) * (cH - 6) - 3

        for i, c in enumerate(win):
            trig = (i == tp)
            up = c["close"] >= c["open"]
            col = gold if trig else (green if up else red)
            cx = x0 + i * cw + cw / 2
            if trig:
                dr.rectangle([x0 + i * cw, y0, x0 + i * cw + cw, y0 + cH], fill=(40, 34, 20))
            dr.line([cx, yy(c["high"]), cx, yy(c["low"])], fill=col, width=2 if trig else 1)
            bt = yy(max(c["open"], c["close"]))
            bb = yy(min(c["open"], c["close"]))
            dr.rectangle([x0 + i * cw + 2, bt, x0 + i * cw + max(3, cw - 4), max(bt + 2, bb)], fill=col)
    dr.text((60, Hc - 46), "Signal preview · deterministic KAOS engine · not financial advice",
            font=font(18), fill=(107, 107, 107))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@share.get("/api/s/{sid}")
async def share_og(sid: str, request: Request, ref: Optional[str] = None):
    """Server-rendered OG/Twitter meta page for `/s/:id` so non-JS crawlers (X, Discord, Slack,
    Facebook) unfurl the signal card richly. Humans are instantly redirected to the SPA page."""
    from fastapi.responses import HTMLResponse
    import html as _html
    doc = await db.signal_shares.find_one({"id": sid}, {"_id": 0})
    from urllib.parse import quote
    from fastapi import HTTPException
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", sid):
        raise HTTPException(status_code=404, detail="Share not found")
    dest = f"/s/{quote(sid, safe='')}" + (f"?ref={quote(ref, safe='')}" if ref else "")
    escaped_dest = _html.escape(dest, quote=True)
    if not doc:
        return HTMLResponse(f"<!doctype html><meta http-equiv=refresh content='0; url={escaped_dest}'>", status_code=404)
    base = str(request.base_url).rstrip("/")
    fwd_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if fwd_host:
        proto = request.headers.get("x-forwarded-proto", "https")
        base = f"{proto}://{fwd_host}"
    img = f"{base}/api/share/{sid}/image.png"
    title = _html.escape(f"KAOS {doc.get('engine')} · {doc.get('direction')} — Trade With KAOS")
    desc = _html.escape(doc.get("reason") or "A deterministic KAOS Strategy signal preview.")
    page = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<meta property='og:type' content='website'>"
        f"<meta property='og:title' content='{title}'>"
        f"<meta property='og:description' content='{desc}'>"
        f"<meta property='og:image' content='{img}'>"
        "<meta property='og:image:width' content='1200'>"
        "<meta property='og:image:height' content='630'>"
        "<meta name='twitter:card' content='summary_large_image'>"
        f"<meta name='twitter:title' content='{title}'>"
        f"<meta name='twitter:description' content='{desc}'>"
        f"<meta name='twitter:image' content='{img}'>"
        f"<meta http-equiv='refresh' content='0; url={dest}'>"
        "</head><body style='background:#0B0B0B;color:#D4AF37;font-family:sans-serif;text-align:center;padding:40px'>"
        f"<p>Opening your KAOS signal…</p><p><a style='color:#22C55E' href='{dest}'>Continue</a></p>"
        f"<script>location.replace({dest!r})</script></body></html>"
    )
    return HTMLResponse(page)


@share.get("/api/share/{sid}/image.png")
async def share_image(sid: str):
    from fastapi.responses import Response
    doc = await db.signal_shares.find_one({"id": sid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Share not found")
    png = _render_share_png(doc)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@mt.post("/mode")
async def set_mode(req: ModeReq, user: dict = Depends(get_current_user)):
    ent = await _check_mode(user, req.mode)
    await db.users.update_one({"id": user["id"]}, {"$set": {"trading_mode": req.mode, "updated_at": now_iso()}})
    return {"mode": req.mode, "entitlements": ent}


@mt.get("/connectors")
async def member_connectors(user: dict = Depends(get_current_user)):
    from services import get_setting
    from services_trading import DEFAULT_CONNECTORS
    return await get_setting("connectors", DEFAULT_CONNECTORS)


@mt.get("/sync-status")
async def sync_status(user: dict = Depends(get_current_user)):
    """Cloud-sync health for the member dashboard: last event received from the extension,
    total events synced, and a per-type breakdown. Powers the connection-health indicator."""
    from datetime import datetime, timezone, timedelta
    match = {"userId": user["id"]}
    total = await db.trade_events.count_documents(match)
    last = await db.trade_events.find_one(match, {"_id": 0}, sort=[("timestamp", -1)])
    last_confirmed = await db.trade_events.find_one({**match, "type": "BROKER_CONFIRMED"},
                                                    {"_id": 0}, sort=[("timestamp", -1)])
    by_type = {}
    async for row in db.trade_events.aggregate([{"$match": match},
                                                {"$group": {"_id": "$type", "n": {"$sum": 1}}}]):
        by_type[row["_id"] or "UNKNOWN"] = row["n"]
    last_at = (last or {}).get("timestamp")
    connected = False
    if last_at:
        try:
            ts = datetime.fromisoformat(str(last_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            connected = (datetime.now(timezone.utc) - ts) < timedelta(minutes=10)
        except Exception:
            connected = False
    return {"totalEvents": total, "lastEventAt": last_at,
            "lastConfirmedAt": (last_confirmed or {}).get("timestamp"),
            "byType": by_type, "connected": connected}


class ReplayReq(BaseModel):
    candles: list
    asset: str = "EURUSD"
    platform: str = "pocket_option"


@mt.post("/strategy-preview")
async def strategy_preview(req: ReplayReq, user: dict = Depends(get_current_user)):
    """Run the REAL deterministic KAOS Berserker strategy over supplied candle history and return
    the most recent confirmed setup (or NO_TRADE). Read-only preview — persists nothing, places no
    order. Requires a plan with bot access."""
    ent = await get_entitlements(user)
    if not ent.get("botAccess"):
        raise HTTPException(status_code=403, detail="Bot access not included in your plan")
    rows = req.candles or []
    if len(rows) < 50:
        raise HTTPException(status_code=400, detail="Provide at least ~50 candle rows: {ts,open,high,low,close}.")
    import asyncio
    import kaos_signature as kaos_berserker
    lo = max(50, len(rows) - 300)

    def _scan():
        for i in range(len(rows), lo, -1):
            sig = kaos_berserker.evaluate(rows[:i])
            if sig:
                return sig, i - 1
        return None, None

    try:
        hit, idx = await asyncio.to_thread(_scan)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed candle rows.")
    from services_trading import get_official_strategy
    cfg = await get_official_strategy()
    return {"decision": "TRADE" if hit else "NO_TRADE", "signal": hit, "barIndex": idx,
            "bars": len(rows), "scanned": len(rows) - lo, "strategyVersion": cfg.get("version"),
            "simulated": False, "live": True}


# ----- admin trading operations -----
admin_dep = require_role("admin")


@at.get("/trading/telemetry")
async def admin_telemetry(admin: dict = Depends(admin_dep)):
    return await telemetry_summary({})


@at.get("/trading/trades")
async def admin_trades(admin: dict = Depends(admin_dep)):
    return await db.trades.find({}, {"_id": 0}).sort("createdAt", -1).to_list(300)


@at.get("/trading/signals")
async def admin_signals(admin: dict = Depends(admin_dep)):
    return await db.signals.find({}, {"_id": 0}).sort("createdAt", -1).to_list(300)


@at.get("/connectors")
async def admin_connectors(admin: dict = Depends(admin_dep)):
    from services import get_setting
    from services_trading import DEFAULT_CONNECTORS
    return await get_setting("connectors", DEFAULT_CONNECTORS)


class ConnectorReq(BaseModel):
    id: str
    name: str
    status: str  # SUPPORTED | COMING_SOON | PLANNED
    note: Optional[str] = ""


@at.post("/connectors")
async def upsert_connector(req: ConnectorReq, admin: dict = Depends(admin_dep)):
    from services import get_setting, set_setting, audit_log
    from services_trading import DEFAULT_CONNECTORS
    conns = await get_setting("connectors", DEFAULT_CONNECTORS)
    found = False
    for c in conns:
        if c["id"] == req.id:
            c.update({"name": req.name, "status": req.status, "note": req.note}); found = True
    if not found:
        conns.append({"id": req.id, "name": req.name, "kind": "broker", "status": req.status, "executionSemantics": {}, "note": req.note})
    await set_setting("connectors", conns)
    await audit_log(admin, "upsert_connector", "connector", req.id, {"status": req.status})
    return {"ok": True, "connectors": conns}


class AiExecutionReq(BaseModel):
    validated: bool
    note: str = Field(default="", max_length=500)


@at.get("/ai-execution")
async def get_ai_execution(admin: dict = Depends(admin_dep)):
    return {"validated": await get_setting(AI_EXECUTION_SETTING, False) is True}


@at.post("/ai-execution")
async def set_ai_execution(req: AiExecutionReq, admin: dict = Depends(admin_dep)):
    await set_setting(AI_EXECUTION_SETTING, req.validated)
    await audit_log(admin, "trading.ai_execution", "settings", AI_EXECUTION_SETTING,
                    {"validated": req.validated, "note": req.note})
    return {"validated": req.validated}


@at.get("/ai-models")
async def admin_ai_models(admin: dict = Depends(admin_dep)):
    return await db.ai_models.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)


class AiModelReq(BaseModel):
    version: str
    status: str = "staged"  # staged | deployed | retired
    notes: Optional[str] = ""


@at.post("/ai-models")
async def add_ai_model(req: AiModelReq, admin: dict = Depends(admin_dep)):
    from services import audit_log
    doc = {"id": new_id("model"), "version": req.version, "status": req.status,
           "notes": req.notes, "simulated": True, "createdAt": now_iso()}
    await db.ai_models.insert_one(dict(doc))
    await audit_log(admin, "register_ai_model", "ai_model", doc["id"], {"version": req.version})
    return clean(doc)


@at.get("/official-strategy")
async def admin_official_strategy(admin: dict = Depends(admin_dep)):
    return {"officialStrategy": await get_official_strategy(), "tradingConfig": await get_trading_config()}


class OfficialStrategyReq(BaseModel):
    officialStrategy: Optional[dict] = None
    tradingConfig: Optional[dict] = None


@at.post("/official-strategy")
async def update_official_strategy(req: OfficialStrategyReq, admin: dict = Depends(admin_dep)):
    from services import set_setting, audit_log
    if req.officialStrategy is not None:
        await set_setting("official_strategy", req.officialStrategy)
    if req.tradingConfig is not None:
        await set_setting("trading_config", req.tradingConfig)
    await audit_log(admin, "update_official_strategy", "strategy", "KAOS")
    return {"ok": True}
