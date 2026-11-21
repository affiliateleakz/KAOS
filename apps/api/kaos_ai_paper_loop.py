"""KAOS experimental AI paper loop: archived closed candles, no broker connectivity.

A directional 1x-notional sandbox, NOT brokerage paper orders or executable
short sales. Model candidates can forecast here without research promotion.
Results, simulated friction, and settlements are permanently journaled.
"""
import asyncio
import math
import os
from datetime import datetime, timezone

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from pymongo.errors import DuplicateKeyError
from db import db, now_iso
from kaos_r2_archive import configured, read_archive, ArchiveUnavailable
from kaos_r2_market_audit import MARKETS
from kaos_r2_ai_lab import LOOKBACK, _features, _score
from kaos_ai_training_jobs import initial_job, JOB_COLLECTION

CONTROL = "kaos_ai_paper_controls"
FORECASTS = "kaos_ai_paper_predictions"
BARS_MS = 60000
MAX_MARKETS_PER_TICK = 4
STALE_MS = 180000
NOTIONAL = 10.0
STARTING_BALANCE = 1000.0
HALF_SPREAD_BPS = 5.0
SLIPPAGE_BPS = 5.0
FEE_BPS_PER_SIDE = 5.0


def probability(rows, model):
    """Return model probability only for 9 contiguous, already-closed bars."""
    if len(rows) < LOOKBACK or any(
        b["ts"] - a["ts"] != BARS_MS for a, b in zip(rows[-LOOKBACK:], rows[-LOOKBACK + 1:])
    ):
        return None
    x = _features(rows, len(rows) - 1)
    if not all(math.isfinite(value) for value in x):
        return None
    p = _score({"x": x}, model)
    return p if math.isfinite(p) and 0 <= p <= 1 else None


def settle_prediction(prediction, exit_price, exit_ts):
    """Return a transparent directional simulation, with spread/slippage/fees."""
    entry = float(prediction["entry_price"])
    notional = float(prediction["notional_usd"])
    side = prediction["direction"]
    if not all(math.isfinite(x) and x > 0 for x in (entry, exit_price, notional)):
        raise ValueError("Invalid settlement price")
    if side not in ("UP", "DOWN"):
        raise ValueError("Invalid direction")
    direction = 1 if side == "UP" else -1
    # Trading cost on entry/exit is charged explicitly, independent of direction.
    gross = notional * direction * (exit_price / entry - 1)
    friction = notional * (2 * (HALF_SPREAD_BPS + SLIPPAGE_BPS + FEE_BPS_PER_SIDE) / 10000)
    pnl = round(gross - friction, 6)
    return {
        "state": "settled", "exit_price": exit_price, "exit_ts": exit_ts,
        "gross_pnl_usd": round(gross, 6), "fees_spread_slippage_usd": round(friction, 6),
        "net_pnl_usd": pnl, "correct_direction": (direction * (exit_price - entry)) > 0,
        "settled_at": now_iso(),
    }


async def tick():
    if not configured() or os.getenv("KAOS_R2_TRAIN_WORKER_ENABLED") != "1":
        return {"status": "disabled", "reason": "R2 training configuration unavailable"}
    owner_id = os.getenv("KAOS_CANDLE_OWNER_USER_ID", "")
    if not owner_id:
        return {"status": "disabled", "reason": "Owner not configured"}
    control = await db[CONTROL].find_one({"_id": owner_id})
    if not control:
        return {"status": "idle", "enabled": False}
    from pymongo import ReturnDocument
    enabled = bool(control.get("enabled", False))
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # Rotate 4/20 markets each minute, including when stopped, to settle existing positions.
    control = await db[CONTROL].find_one_and_update(
        {"_id": owner_id}, {"$inc": {"next_market_index": MAX_MARKETS_PER_TICK}},
        return_document=ReturnDocument.BEFORE
    )
    start = int(control.get("next_market_index", 0)) % len(MARKETS)
    batch = [MARKETS[(start + i) % len(MARKETS)] for i in range(MAX_MARKETS_PER_TICK)]
    result = {"status": "running" if enabled else "paused", "markets_checked": 0,
              "predictions": 0, "settled": 0, "skipped": 0, "errors": 0}

    for symbol, asset_class in batch:
        try:
            open_position = await db[FORECASTS].find_one({
                "owner_id": owner_id, "symbol": symbol, "state": "open"})
            model = None
            if enabled and not open_position:
                model = await db.kaos_r2_research_models.find_one({
                    "owner_id": owner_id, "symbol": symbol, "asset_class": asset_class,
                    "strategy": "R2_OHLC_LOGISTIC_V1", "status": {"$in": ["candidate", "research_active"]}
                }, sort=[("created_at", -1)])
            if not open_position and not model:
                result["skipped"] += 1
                continue
            horizon = int(open_position["horizon_bars"] if open_position else model.get("horizon_bars", 4))
            if not 1 <= horizon <= 30:
                result["skipped"] += 1
                continue
            candles, source = await read_archive(symbol, asset_class, 60, limit=300)
            result["markets_checked"] += 1
            if not candles:
                result["skipped"] += 1
                continue
            latest = candles[-1]
            if open_position:
                target = open_position["target_ts"]
                exit_candle = next((r for r in candles if r["ts"] == target and r["ts"] + BARS_MS <= now_ms), None)
                if exit_candle:
                    settlement = settle_prediction(open_position, float(exit_candle["close"]), target)
                    changed = await db[FORECASTS].update_one(
                        {"_id": open_position["_id"], "state": "open"},
                        {"$set": settlement})
                    result["settled"] += changed.modified_count
                elif latest["ts"] > target + 60 * BARS_MS:
                    # Missing horizon candle is not a loss, win, or fabricated fill.
                    await db[FORECASTS].update_one(
                        {"_id": open_position["_id"], "state": "open"},
                        {"$set": {"state": "unresolved", "reason": "Missing exact settlement candle",
                                  "updated_at": now_iso()}})
                # Do not open a second position on the same market in this invocation.
                continue
            # An archived candle is NOT a live quote; require a nearly-current closed bar.
            if not enabled or latest["ts"] + BARS_MS > now_ms or now_ms - (latest["ts"] + BARS_MS) > STALE_MS:
                result["skipped"] += 1
                continue
            if source != model.get("source"):
                result["skipped"] += 1
                continue
            p = probability(candles, model["model"])
            if p is None:
                result["skipped"] += 1
                continue
            direction = "UP" if p >= 0.5 else "DOWN"
            ts = int(latest["ts"])
            document = {
                "_id": "aipaper:%s:%s:%s" % (owner_id, symbol, ts),
                "owner_id": owner_id, "symbol": symbol, "asset_class": asset_class,
                "source": source, "model_id": model["id"], "direction": direction,
                "prob_up": round(p, 6), "confidence": round(max(p, 1-p), 6),
                "entry_price": float(latest["close"]), "entry_ts": ts,
                "target_ts": ts + horizon * BARS_MS, "horizon_bars": horizon,
                "notional_usd": NOTIONAL, "state": "open", "created_at": now_iso(),
                "fill_type": "archived_closed_candle_simulation",
                "paper_only": True, "broker_order": False,
                "simulation": "1x directional outcome, not actual stock/crypto order or broker fill"
            }
            try:
                await db[FORECASTS].insert_one(document)
                result["predictions"] += 1
            except DuplicateKeyError:
                result["skipped"] += 1
        except (ArchiveUnavailable, ValueError, KeyError, RuntimeError, TypeError, OSError):
            result["errors"] += 1

    if enabled and result["settled"]:
        # Feed newly closed real market candles into the established R2 trainer.
        # Retrain after 50 additional labeled paper outcomes; keep existing candidates
        # until a fresh model is fitted, never activate a real-money trading model.
        settled = await db[FORECASTS].count_documents({"owner_id": owner_id, "state": "settled"})
        last_count = int(control.get("last_retrain_settled", 0))
        if settled - last_count >= 50:
            pending = await db[JOB_COLLECTION].count_documents({
                "owner_id": owner_id, "status": {"$in": ["queued", "running"]}})
            if not pending:
                job = initial_job(owner_id, "all", "BTC-USD", 5000, 4)
                await db[JOB_COLLECTION].insert_one(job)
                await db[CONTROL].update_one(
                    {"_id": owner_id, "last_retrain_settled": last_count},
                    {"$set": {"last_retrain_settled": settled, "last_retrain_at": now_iso()}})
                result["retraining_queued"] = True
    return result


async def status(owner_id):
    control = await db[CONTROL].find_one({"_id": owner_id}, {"_id": 0})
    recent = await db[FORECASTS].find(
        {"owner_id": owner_id}, {"_id": 0}
    ).sort("created_at", -1).limit(30).to_list(length=30)
    settled = await db[FORECASTS].find(
        {"owner_id": owner_id, "state": "settled"},
        {"_id": 0, "net_pnl_usd": 1, "correct_direction": 1}
    ).to_list(length=5000)
    net = round(sum(float(r.get("net_pnl_usd", 0)) for r in settled), 4)
    wins = sum(bool(r.get("correct_direction")) for r in settled)
    return {"enabled": bool((control or {}).get("enabled")), "mode": "experimental_paper",
            "broker_orders_enabled": False, "initial_balance_usd": STARTING_BALANCE,
            "simulated_equity_usd": round(STARTING_BALANCE + net, 4),
            "realized_net_pnl_usd": net, "settled": len(settled), "direction_correct": wins,
            "direction_accuracy": round(wins / len(settled), 4) if settled else None,
            "recent": recent,
            "note": "R2 closed-candle directional 1x notional simulation; fills are not broker quotes. No live orders."}


if __name__ == "__main__":
    print(asyncio.run(tick()))
