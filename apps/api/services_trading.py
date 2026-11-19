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
AI_EXECUTION_MODES = {"AI", "STRATEGY_AI"}
AI_EXECUTION_SETTING = "ai_execution_validated"


async def apply_ai_execution_lock(ent: dict) -> dict:
    """AI-controlled modes stay off until an admin records independent validation (spec §10)."""
    from services import get_setting
    if await get_setting(AI_EXECUTION_SETTING, False) is True:
        return {**ent, "aiExecutionLocked": False}
    modes = [m for m in (ent.get("modes") or []) if m not in AI_EXECUTION_MODES]
    return {**ent, "modes": modes, "aiExecutionLocked": True}

# Default KAOS Strategy metadata (owner-configurable via admin). This is DISPLAY METADATA only;
# the tested execution logic lives in kaos_signature.py / candidate7b_strategy.js (see STRATEGY_ENGINE.md).
DEFAULT_OFFICIAL_STRATEGY = {
    "name":"KAOS Strategy","type":"OFFICIAL","version":"SR1.1","locked":True,
    "engine":"SUPPORT_RESISTANCE","signalTimeframe":"5s","expirations":["15s","20s","25s"],
    "srLookback":20,"contextTimeframe":"60s","emaFast":9,"emaSlow":21,
    "description":"Trend-aligned support/resistance rejection, sweep/reclaim, breakout/retest and pullback continuation; closed-candle confirmation.",
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
    "cloudStrategies": False, "community": True, "premiumTools": False, "deviceLimit": 1, "chartLimit": 1,
}


async def get_official_strategy():
    metadata = await get_setting("official_strategy", DEFAULT_OFFICIAL_STRATEGY)
    if metadata.get("engine") == "TWO_CANDLE_CONTINUATION" or metadata.get("version") == "C9.0":
        return dict(DEFAULT_OFFICIAL_STRATEGY)
    if metadata.get("name") in {"KAOS Berserker", "Berserker", "Candidate 7B", "candidate"}:
        return {**metadata, "name": "KAOS Strategy"}
    return metadata


async def get_trading_config():
    return await get_setting("trading_config", DEFAULT_TRADING_CONFIG)


# Free tier: the bot in KAOS Strategy mode on one device; no AI modes, scanners or premium tools.
FREE_ENTITLEMENTS = {
    "botAccess": True, "modes": ["STRATEGY"], "connectors": ["pocket_option"], "scanners": False,
    "aiInsights": False, "cloudStrategies": False, "community": True, "premiumTools": False, "deviceLimit": 1,
    "chartLimit": 1, "aiTraining": False, "pretrainedModels": False, "aiSignals": False,
    "tier": "free",
}


async def get_entitlements(user: dict) -> dict:
    from device_policy import device_entitlements
    # Server-stored super-admin role carries the full feature tier without a
    # paid subscription. This never changes billing records or AI validation.
    if (user.get("role") == "super_admin"
            and user.get("account_status", "active") not in ("suspended", "banned")
            and not user.get("extension_access_revoked")):
        return device_entitlements(user, await apply_ai_execution_lock({
            "botAccess": True, "modes": list(TRADING_MODES), "connectors": ["pocket_option"],
            "scanners": True, "aiInsights": True, "aiTraining": True, "pretrainedModels": True, "aiSignals": True, "cloudStrategies": True,
            "community": True, "premiumTools": True, "chartLimit": 4,
            "deviceLimit": None, "tier": "ultimate", "roleGranted": True,
        }))
    return device_entitlements(user, await _membership_entitlements(user))


async def _membership_entitlements(user: dict) -> dict:
    """Feature entitlements derived from the user's active plan. Admin-configurable, never hardcoded per-component."""
    from routes_billing import get_plans, find_plan
    if user.get("account_status", "active") in ("suspended", "banned"):
        return {**DEFAULT_ENTITLEMENTS, "botAccess": False}
    if user.get('membership_status')=='TRIAL':
        from subscription_trial import trial_expired
        if trial_expired(user):return {**FREE_ENTITLEMENTS,'botAccess':False,'modes':[]}
    if user.get("membership_status") not in ("ACTIVE", "TRIAL"):
        return {**FREE_ENTITLEMENTS,**({"botAccess":False,"modes":[]} if user.get("bot_trial_required") or user.get("pro_trial_ends_at") else {})}
    plan = find_plan(await get_plans(), user.get("membership_plan"))
    ent = (plan or {}).get("entitlements")
    if not ent:
        return {**DEFAULT_ENTITLEMENTS, "botAccess": True, "modes": ["STRATEGY"], "connectors": ["pocket_option"],
                "cloudStrategies": True, "scanners": True, "aiInsights": True, "aiTraining": True, "pretrainedModels": False, "aiSignals": False, "tier": "pro"}
    return await apply_ai_execution_lock({"scanners": True, "aiInsights": True, **ent, "aiTraining": True, "pretrainedModels": plan.get("tier", "pro") == "ultimate", "aiSignals": plan.get("tier", "pro") == "ultimate", "tier": plan.get("tier", "pro")})


def _pseudo(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16)


def _engine_label(cfg: dict, key: str) -> str:
    for e in cfg.get("engines", []):
        if e.get("key") == key:
            return e.get("label", key)
    return key


async def kaos_strategy_predict(asset: str, platform: str, context: dict) -> dict:
    """Real deterministic KAOS Strategy — execution authority.

    When candle rows are supplied (context.candles / context.rows), the ported support/resistance
    strategy runs and returns a REAL, non-simulated decision. Without market data it falls back
    to a clearly-flagged simulated placeholder so the boundary never silently returns nothing.
    """
    import kaos_signature as kaos_berserker
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
                "reason": "No confirmed support/resistance setup; complete 5s/15s/30s and 24 completed 60s context bars are required.",
                "strategyVersion": cfg.get("version"), "simulated": False, "live": True}
    # Missing completed candles MUST NOT produce a tradeable signal.
    return {"source": "STRATEGY", "engine": None, "direction": None,
            "decision": "NO_DATA", "reason": "At least 50 closed candles required",
            "strategyVersion": cfg.get("version"), "simulated": False, "live": False}


async def kaos_ai_predict(asset: str, platform: str, context: dict, user: dict = None) -> dict:
    """Real KAOS AI server-side inference (learning/reporting only — no execution authority).

    When a model is deployed with a portable tree bundle AND a feature vector is supplied
    (context.featureVector / context.x), the native tree bundle is evaluated in-process. Without
    a real bundle or feature vector it falls back to a clearly-flagged simulated placeholder.
    """
    if user is not None:
        from training_service import predict_for_member
        expiry = str(context.get("expiration", "20s"))
        if expiry not in ("15s", "20s", "25s", "30s", "45s", "60s"):raise ValueError("Unsupported model horizon")
        return await predict_for_member(user, context.get("featureVector") or context.get("x"), f"{platform}:binary:5s:{expiry}:real")
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
    # Missing model/data must never masquerade as a market prediction.
    return {
        "source": "AI", "direction": None, "expiration": None, "confidence": None,
        "reason": "No deployed model bundle and valid feature vector available",
        "modelVersion": tc.get("aiModelVersion"), "authority": "LEARNING_ONLY",
        "simulated": True, "live": False,
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
