"""KAOS trading services: entitlements, strategy/AI integration boundaries, telemetry.

The REAL KAOS Strategy engines (Reversal/Runner/Breakout) and KAOS AI models live on
infrastructure the owner controls and are integrated later. Everything here is an
integration boundary. Placeholder intelligence is clearly flagged `simulated: True` so it
can never be mistaken for the real proprietary implementation.
"""
import hashlib
from db import db
from services import get_setting

# Explicit trade execution lifecycle. A signal is NOT a trade; broker confirmation is the
# boundary between an attempted order and an actual trade.
TRADE_STATES = [
    "SIGNAL_GENERATED", "SIGNAL_DELIVERED", "ORDER_SUBMIT_ATTEMPT",
    "BROKER_CONFIRMED", "TRADE_OPEN", "TRADE_RESULT", "ORDER_FAILED",
]
TRADING_MODES = ["STRATEGY", "AI", "STRATEGY_AI"]

# Default KAOS Berserker metadata (owner-configurable via admin). This is DISPLAY METADATA only;
# the tested execution logic lives in kaos_berserker.py / candidate7b_strategy.js (see STRATEGY_ENGINE.md).
DEFAULT_OFFICIAL_STRATEGY = {
    "name": "KAOS Berserker",
    "type": "OFFICIAL",
    "version": "C9.0",
    "locked": True,
    "engine": "TWO_CANDLE_CONTINUATION",
    "signalTimeframe": "5s",
    "expiration": "45s",
    "emaFast": 9,
    "emaSlow": 21,
    "atrPeriod": 20,
    "pullbackCandles": 2,
    "pullbackRule": "Exactly 2 counter-trend pullback candles",
    "maxPullbackAtr": 1.35,
    "minConfirmBodyFrac": 0.45,
    "description": ("Established trend -> exactly 2 counter-trend pullback candles -> continuation "
                    "confirmation candle -> next-candle entry."),
}

# Trading decision config (execution authority / combine rules) is versioned config, NOT
# hardcoded thresholds. Owner tunes these later via admin settings.
DEFAULT_TRADING_CONFIG = {
    "executionAuthority": "STRATEGY",   # STRATEGY | AI | STRATEGY_AI
    "combineRule": "authority_only",     # placeholder handle; real rules configured later
    "aiModelVersion": "kaos-ai-0.1.0-sim",
}

DEFAULT_CONNECTORS = [
    {"id": "pocket_option", "name": "Pocket Option", "kind": "broker", "status": "SUPPORTED",
     "executionSemantics": {"expirations": ["15s", "30s"], "orderType": "binary"},
     "note": "First integration. Browser-based order submission handled by KAOS Trading Bot."},
    {"id": "mt4_mt5", "name": "MetaTrader 4/5", "kind": "broker", "status": "PLANNED",
     "executionSemantics": {}, "note": "Planned. Execution semantics differ from binary expirations."},
    {"id": "oanda", "name": "OANDA", "kind": "broker", "status": "PLANNED", "executionSemantics": {}, "note": "Planned."},
    {"id": "interactive_brokers", "name": "Interactive Brokers", "kind": "broker", "status": "PLANNED", "executionSemantics": {}, "note": "Planned."},
    {"id": "alpaca", "name": "Alpaca", "kind": "broker", "status": "PLANNED", "executionSemantics": {}, "note": "Planned."},
]

DEFAULT_ENTITLEMENTS = {
    "botAccess": False, "modes": [], "connectors": [],
    "cloudStrategies": False, "community": True, "premiumTools": False, "deviceLimit": 1,
}


async def get_official_strategy():
    return await get_setting("official_strategy", DEFAULT_OFFICIAL_STRATEGY)


async def get_trading_config():
    return await get_setting("trading_config", DEFAULT_TRADING_CONFIG)


async def get_entitlements(user: dict) -> dict:
    """Feature entitlements derived from the user's active plan. Admin-configurable, never hardcoded per-component."""
    from routes_billing import get_plans
    active = user.get("membership_status") in ("ACTIVE", "TRIAL")
    if not active:
        return {**DEFAULT_ENTITLEMENTS, "botAccess": False}
    plans = await get_plans()
    plan = next((p for p in plans if p["id"] == user.get("membership_plan")), None)
    ent = (plan or {}).get("entitlements") if plan else None
    return ent or {**DEFAULT_ENTITLEMENTS, "botAccess": True, "modes": ["STRATEGY"],
                   "connectors": ["pocket_option"], "cloudStrategies": True}


def _pseudo(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16)


def _engine_label(cfg: dict, key: str) -> str:
    for e in cfg.get("engines", []):
        if e.get("key") == key:
            return e.get("label", key)
    return key


async def kaos_strategy_predict(asset: str, platform: str, context: dict) -> dict:
    """Real deterministic KAOS Berserker (Candidate 7B) strategy — execution authority.

    When candle rows are supplied (context.candles / context.rows), the ported three-engine
    strategy runs and returns a REAL, non-simulated decision. Without market data it falls back
    to a clearly-flagged simulated placeholder so the boundary never silently returns nothing.
    """
    import kaos_berserker
    cfg = await get_official_strategy()
    candles = context.get("candles") or context.get("rows") or context.get("candleHistory")
    if candles and len(candles) >= 50:
        try:
            sig = kaos_berserker.evaluate(candles)
        except Exception as exc:  # malformed candle rows must not crash the pipeline
            return {"source": "STRATEGY", "engine": None, "direction": None, "decision": "ERROR",
                    "reason": f"strategy_error: {exc}", "strategyVersion": cfg.get("version"),
                    "simulated": False, "live": True}
        if sig:
            return {"source": "STRATEGY", "engine": sig["engine"],
                    "engineLabel": _engine_label(cfg, sig["engine"]),
                    "direction": sig["direction"], "expiration": sig["expiration"],
                    "confidence": sig["confidence"], "reason": sig.get("reason"),
                    "overlap": sig.get("overlap"), "decision": "TRADE",
                    "strategyVersion": cfg.get("version"), "simulated": False, "live": True}
        return {"source": "STRATEGY", "engine": None, "direction": None, "decision": "NO_TRADE",
                "reason": "No confirmed Reversal/Runner/Breakout setup (or opposite-direction conflict).",
                "strategyVersion": cfg.get("version"), "simulated": False, "live": True}
    # Missing completed candles MUST NOT produce a tradeable signal.
    return {"source": "STRATEGY", "engine": None, "direction": None,
            "decision": "NO_DATA", "reason": "At least 50 closed candles required",
            "strategyVersion": cfg.get("version"), "simulated": False, "live": False}


async def kaos_ai_predict(asset: str, platform: str, context: dict) -> dict:
    """Real KAOS AI server-side inference (learning/reporting only — no execution authority).

    When a model is deployed with a portable tree bundle AND a feature vector is supplied
    (context.featureVector / context.x), the native tree bundle is evaluated in-process. Without
    a real bundle or feature vector it falls back to a clearly-flagged simulated placeholder.
    """
    tc = await get_trading_config()
    features = context.get("featureVector") or context.get("x")
    if not isinstance(features, list):
        features = None
    model = await db.ai_models.find_one({"status": "deployed", "bundle": {"$ne": None}},
                                        {"_id": 0}, sort=[("createdAt", -1)])
    if model and model.get("bundle") and isinstance(features, list) and features:
        try:
            import kaos_ai_infer
            out = kaos_ai_infer.predict(model["bundle"], features, asset)
            return {"source": "AI", "direction": out["direction"], "expiration": "30s",
                    "confidence": out["confidence"], "probUp": out["prob_up"],
                    "modelKind": out["modelKind"], "modelVersion": model.get("version"),
                    "authority": "LEARNING_ONLY", "simulated": False, "live": True}
        except Exception as exc:
            return {"source": "AI", "direction": None, "confidence": None,
                    "reason": f"inference_error: {exc}", "authority": "LEARNING_ONLY",
                    "modelVersion": model.get("version"), "simulated": False, "live": True}
    # ---- simulated fallback (no deployed bundle or no feature vector) ----
    h = _pseudo("ai", asset, platform, context.get("bucket", ""))
    return {
        "source": "AI", "direction": "BUY" if (h >> 2) % 2 == 0 else "SELL",
        "expiration": "30s", "confidence": round(0.5 + (h % 40) / 100.0, 2),
        "modelVersion": tc.get("aiModelVersion"), "authority": "LEARNING_ONLY", "simulated": True,
    }


async def telemetry_summary(match: dict = None):
    match = match or {}
    trades = await db.trades.find(match).to_list(5000)
    signals_count = await db.signals.count_documents(match)
    by_state, by_result, by_engine, by_mode, by_fail = {}, {}, {}, {}, {}
    pnl = 0.0
    for t in trades:
        by_state[t.get("state")] = by_state.get(t.get("state"), 0) + 1
        if t.get("result"):
            by_result[t["result"]] = by_result.get(t["result"], 0) + 1
        if t.get("engine"):
            by_engine[t["engine"]] = by_engine.get(t["engine"], 0) + 1
        if t.get("tradingMode"):
            by_mode[t["tradingMode"]] = by_mode.get(t["tradingMode"], 0) + 1
        if t.get("failureCode"):
            by_fail[t["failureCode"]] = by_fail.get(t["failureCode"], 0) + 1
        pnl += t.get("pnl") or 0
    confirmed = by_state.get("BROKER_CONFIRMED", 0) + by_state.get("TRADE_OPEN", 0) + by_state.get("TRADE_RESULT", 0)
    attempts = by_state.get("ORDER_SUBMIT_ATTEMPT", 0) + confirmed + by_state.get("ORDER_FAILED", 0)
    wins = by_result.get("WIN", 0)
    resolved = wins + by_result.get("LOSS", 0) + by_result.get("TIE", 0)
    return {
        "signals": signals_count, "orderAttempts": attempts, "brokerConfirmed": confirmed,
        "failed": by_state.get("ORDER_FAILED", 0), "results": resolved,
        "winRate": round((wins / resolved) * 100, 2) if resolved else None,
        "netPnl": round(pnl, 2), "byState": by_state, "byResult": by_result,
        "byEngine": by_engine, "byMode": by_mode, "byFailure": by_fail,
    }
