from fastapi import APIRouter, HTTPException, Depends
from db import db, new_id, now_iso, clean
from auth import get_current_user
from services import public_user, notify
from models import (StrategyReq, VisibilityReq, BacktestReq, IndicatorReq, ScriptReq)

router = APIRouter(prefix="/api", tags=["strategies"])

BUILT_IN = "BUILT_IN"
CUSTOM = "CUSTOM"


def strat_public(s, owner=None):
    s = clean(dict(s))
    if owner:
        s["owner"] = public_user(owner)
    return s


async def _snapshot_version(strat, changelog=""):
    await db.strategy_versions.insert_one({
        "id": new_id("sv"), "strategyId": strat["id"], "version": strat["version"],
        "name": strat["name"], "description": strat.get("description"),
        "indicators": strat.get("indicators"), "indicatorSettings": strat.get("indicatorSettings"),
        "rules": strat.get("rules"), "parameters": strat.get("parameters"),
        "signalTimeframe": strat.get("signalTimeframe"), "expiry": strat.get("expiry"),
        "changelog": changelog, "createdAt": now_iso()})


# ---------- My strategies ----------
@router.get("/strategies")
async def list_my_strategies(user: dict = Depends(get_current_user)):
    docs = await db.strategies.find({"ownerUserId": user["id"]}, {"_id": 0}).sort("updatedAt", -1).to_list(500)
    return docs


@router.post("/strategies")
async def create_strategy(req: StrategyReq, user: dict = Depends(get_current_user)):
    vis = req.visibility if req.visibility in ("PRIVATE", "UNLISTED", "PUBLIC") else "PRIVATE"
    doc = {
        "id": new_id("strat"), "ownerUserId": user["id"], "ownerUsername": user.get("username"),
        "name": req.name, "description": req.description, "version": 1,
        "type": CUSTOM, "editable": True, "locked": False,
        "visibility": "PRIVATE",  # never auto-publish; publish is explicit
        "engineType": req.engineType, "signalTimeframe": req.signalTimeframe, "expiry": req.expiry,
        "indicators": req.indicators, "indicatorSettings": req.indicatorSettings,
        "rules": req.rules, "parameters": req.parameters, "tags": req.tags, "category": req.category,
        "published": False, "publishedAt": None,
        "forkedFromStrategyId": None, "forkedFromVersion": None,
        "likesCount": 0, "savesCount": 0, "forksCount": 0, "commentsCount": 0,
        "createdAt": now_iso(), "updatedAt": now_iso(),
    }
    await db.strategies.insert_one(dict(doc))
    await _snapshot_version(doc, "Initial version")
    return clean(doc)


@router.get("/strategies/{sid}")
async def get_strategy(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s["visibility"] == "PRIVATE" and s["ownerUserId"] != user["id"] and user.get("role") == "user":
        raise HTTPException(status_code=403, detail="Private strategy")
    versions = await db.strategy_versions.find({"strategyId": sid}, {"_id": 0}).sort("version", -1).to_list(100)
    owner = await db.users.find_one({"id": s["ownerUserId"]})
    out = strat_public(s, owner)
    out["versions"] = versions
    return out


@router.put("/strategies/{sid}")
async def update_strategy(sid: str, req: StrategyReq, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s["ownerUserId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your strategy")
    if s.get("locked") or s.get("type") == BUILT_IN:
        raise HTTPException(status_code=403, detail="Strategy is locked")
    new_version = s["version"] + 1
    updates = {**req.model_dump(exclude={"visibility", "changelog"}), "version": new_version, "updatedAt": now_iso()}
    await db.strategies.update_one({"id": sid}, {"$set": updates})
    s.update(updates)
    await _snapshot_version(s, req.changelog or f"v{new_version}")
    # notify followers who saved/installed
    installs = await db.strategy_installations.find({"strategyId": sid}).to_list(1000)
    for ins in installs:
        if ins["userId"] != user["id"]:
            await notify(ins["userId"], "strategy_update", f"{s['name']} updated to v{new_version}", f"/community/{sid}", user)
    return clean(await db.strategies.find_one({"id": sid}))


@router.delete("/strategies/{sid}")
async def delete_strategy(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s["ownerUserId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your strategy")
    await db.strategies.delete_one({"id": sid})
    await db.strategy_versions.delete_many({"strategyId": sid})
    return {"deleted": True}


@router.post("/strategies/{sid}/publish")
async def publish_strategy(sid: str, user: dict = Depends(get_current_user), req: VisibilityReq | None = None):
    s = await db.strategies.find_one({"id": sid})
    if not s or s["ownerUserId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    vis = req.visibility if (req and req.visibility in ("UNLISTED", "PUBLIC")) else "PUBLIC"
    await db.strategies.update_one({"id": sid}, {"$set": {"visibility": vis, "published": True, "publishedAt": now_iso(), "updatedAt": now_iso()}})
    return {"published": True, "visibility": vis}


@router.post("/strategies/{sid}/unpublish")
async def unpublish_strategy(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or s["ownerUserId"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.strategies.update_one({"id": sid}, {"$set": {"visibility": "PRIVATE", "published": False, "updatedAt": now_iso()}})
    return {"published": False}


# ---------- Indicators ----------
@router.get("/indicators")
async def list_indicators(user: dict = Depends(get_current_user)):
    docs = await db.indicators.find({"$or": [{"ownerUserId": user["id"]}, {"visibility": "PUBLIC"}, {"type": "BUILT_IN"}]}, {"_id": 0}).to_list(500)
    return docs


@router.post("/indicators")
async def create_indicator(req: IndicatorReq, user: dict = Depends(get_current_user)):
    doc = {"id": new_id("ind"), "ownerUserId": user["id"], "author": user.get("username"),
           "name": req.name, "description": req.description, "category": req.category,
           "parameters": req.parameters, "version": 1, "type": CUSTOM,
           "visibility": req.visibility if req.visibility in ("PRIVATE", "UNLISTED", "PUBLIC") else "PRIVATE",
           "createdAt": now_iso(), "updatedAt": now_iso()}
    await db.indicators.insert_one(dict(doc))
    return clean(doc)


# ---------- Scripts (storage only, never executed) ----------
@router.get("/scripts")
async def list_scripts(user: dict = Depends(get_current_user)):
    docs = await db.scripts.find({"$or": [{"ownerUserId": user["id"]}, {"visibility": "PUBLIC"}]}, {"_id": 0}).to_list(500)
    return docs


@router.post("/scripts")
async def create_script(req: ScriptReq, user: dict = Depends(get_current_user)):
    sid = new_id("script")
    doc = {"id": sid, "ownerUserId": user["id"], "author": user.get("username"),
           "name": req.name, "description": req.description, "sourceType": req.sourceType,
           "version": 1, "tags": req.tags,
           "visibility": req.visibility if req.visibility in ("PRIVATE", "UNLISTED", "PUBLIC") else "PRIVATE",
           "createdAt": now_iso(), "updatedAt": now_iso()}
    await db.scripts.insert_one(dict(doc))
    # store source as an untrusted, never-executed version blob
    await db.script_versions.insert_one({"id": new_id("scv"), "scriptId": sid, "version": 1,
                                         "source": req.source, "executed": False, "createdAt": now_iso()})
    return clean(doc)


# ---------- Backtests ----------
@router.get("/backtests")
async def list_backtests(user: dict = Depends(get_current_user)):
    docs = await db.backtest_reports.find({"ownerUserId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return docs


@router.post("/backtests")
async def create_backtest(req: BacktestReq, user: dict = Depends(get_current_user)):
    total = max(req.trades, 1)
    win_rate = round((req.wins / total) * 100, 2)
    doc = {"id": new_id("bt"), "ownerUserId": user["id"], "strategyId": req.strategyId,
           "strategyVersion": req.strategyVersion, "market": req.market, "timeframe": req.timeframe,
           "expiry": req.expiry, "sampleStart": req.sampleStart, "sampleEnd": req.sampleEnd,
           "trades": req.trades, "wins": req.wins, "losses": req.losses, "ties": req.ties,
           "winRate": win_rate, "maxLossStreak": None,
           "provenance": "manual", "verified": False, "createdAt": now_iso()}
    await db.backtest_reports.insert_one(dict(doc))
    return clean(doc)
