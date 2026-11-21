"""Offline, owner-operated KAOS R2 backtest batch. Research only; no orders.

Reads completed 1-minute R2 candles for the currently configured 20 markets,
runs the deterministic KAOS Structure Research strategy when bars are
continuous, and saves a timestamped immutable JSON report under the active
backend's private reports directory. No model is trained/promoted.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)

from kaos_r2_archive import configured, read_archive, ArchiveUnavailable
from kaos_r2_market_audit import MARKETS
from kaos_r2_research import structure_replay_from_archive

STRATEGY = "KAOS_STRUCTURE_RESEARCH_V1"
HORIZONS = (1, 2, 3, 5, 10)
MIN_LOOKBACK = 12

def summarize_market(symbol, asset_class, candles, source, *, seconds=60,
                     expiry_bars=4, lookback=MIN_LOOKBACK):
    """Pure, deterministic summary; independent of R2 and file IO."""
    outcome = structure_replay_from_archive(
        candles, seconds, expiry_bars=expiry_bars, lookback=lookback
    )
    return {
        "symbol": symbol, "asset_class": asset_class,
        "source": source, "seconds": seconds,
        "expiry_bars": expiry_bars, "lookback": lookback,
        "status": outcome["status"],
        "history": outcome["history"],
        "summary": outcome.get("summary"),
        "trades": outcome.get("trades", []),
        "research_only": True, "execution_enabled": False,
        "notes": outcome.get("message"),
    }

async def collect_report(*, expiry_bars=4, lookback=MIN_LOOKBACK, limit=300,
                         markets=MARKETS, reader=read_archive, now=None):
    """Bounded parallel reads; failures stay visible instead of hiding a market."""
    if not 1 <= expiry_bars <= 240 or not 5 <= lookback <= 100:
        raise ValueError("Invalid expiry/lookback")
    if not 100 <= limit <= 5000:
        raise ValueError("limit must be 100..5000")
    now = now or datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    semaphore = asyncio.Semaphore(3)

    async def run_one(symbol, asset_class):
        async with semaphore:
            try:
                rows, source = await reader(symbol, asset_class, 60,
                                            limit=limit, now_ms=now_ms)
                return summarize_market(
                    symbol, asset_class, rows, source,
                    expiry_bars=expiry_bars, lookback=lookback
                )
            except (ArchiveUnavailable, ValueError, RuntimeError, OSError) as exc:
                return {
                    "symbol": symbol, "asset_class": asset_class,
                    "status": "read_or_validation_error",
                    "error_type": type(exc).__name__,
                    "summary": None, "trades": [],
                    "research_only": True, "execution_enabled": False,
                }

    results = await asyncio.gather(*(run_one(*market) for market in markets))
    completed = [r for r in results if r["status"] == "completed"]
    evaluated = len(completed)
    trades = sum(r["summary"]["trades"] for r in completed)
    wins = sum(r["summary"]["wins"] for r in completed)
    losses = sum(r["summary"]["losses"] for r in completed)
    ties = sum(r["summary"]["ties"] for r in completed)
    decisive = wins + losses
    return {
        "schema": "kaos_r2_research_batch_v1",
        "generated_at_utc": now.isoformat(),
        "strategy": STRATEGY,
        "source": "private_cloudflare_r2",
        "timeframe_seconds": 60,
        "expiry_bars": expiry_bars,
        "lookback": lookback,
        "request_limit": limit,
        "research_only": True,
        "execution_enabled": False,
        "train_ai": False,
        "model_approved": False,
        "assumptions": {
            "entry": "next_bar_open_after_closed_signal",
            "exit": "expiry_bar_open",
            "fill_model": "idealized_ohlc_directional_only",
            "fees_spread_slippage_payout": "not_modeled",
            "missing_intervals": "entire_market_backtest_blocked",
            "interpretation": "not_live_executable_or_profitability_evidence",
        },
        "aggregate": {
            "markets_requested": len(markets),
            "markets_evaluated": evaluated,
            "markets_skipped": len(markets)-evaluated,
            "trades": trades, "wins": wins, "losses": losses, "ties": ties,
            "win_rate_ex_ties": round(100 * wins/decisive, 2) if decisive else None,
            "trades_per_hour": None,
            "note": "Pooled win rate is descriptive only; mixed markets and differing coverage make a combined trades/hour misleading",
        },
        "markets": results,
    }

def write_report(report, out_dir):
    """Use exclusive creation; never overwrite reports or follow output symlinks."""
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink():
        raise ValueError("Refusing symlink report directory")
    name = "kaos-r2-backtest-" + report["generated_at_utc"].replace(":", "-").replace("+", "_") + ".json"
    path = directory / name
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path

def main():
    parser = argparse.ArgumentParser(description="KAOS R2 research-only 20-market backtest")
    parser.add_argument("--limit", type=int, default=300, choices=range(100, 5001),
                        metavar="100..5000")
    parser.add_argument("--expiry-bars", type=int, default=4)
    parser.add_argument("--lookback", type=int, default=12)
    parser.add_argument("--report-dir", default=str(ROOT / "research-reports"))
    args = parser.parse_args()
    if not configured():
        print("KAOS R2 is not enabled in the active backend .env", file=sys.stderr)
        return 2
    report = asyncio.run(collect_report(
        expiry_bars=args.expiry_bars, lookback=args.lookback, limit=args.limit
    ))
    path = write_report(report, args.report_dir)
    print(f"KAOS RESEARCH BATCH: {report['generated_at_utc']}")
    print(f"Strategy: {STRATEGY}; {args.expiry_bars}-bar expiry; closed 60s candles")
    print(f"{'MARKET':<12} {'RESULT':<33} {'BARS':>5} {'TRADES':>6} {'W':>4} {'L':>4} {'T':>4} {'WR%':>7}")
    for item in report["markets"]:
        counts = item.get("summary") or {}
        hist = item.get("history") or {}
        wr = counts.get("win_rate_ex_ties")
        print(f"{item['symbol']:<12} {item['status']:<33} {hist.get('bars',0):>5} "
              f"{counts.get('trades',0):>6} {counts.get('wins',0):>4} "
              f"{counts.get('losses',0):>4} {counts.get('ties',0):>4} "
              f"{'-' if wr is None else f'{wr:.2f}':>7}")
    aggregate = report["aggregate"]
    print(f"Evaluated: {aggregate['markets_evaluated']}/{aggregate['markets_requested']}; "
          f"trades: {aggregate['trades']}; W/L/T: "
          f"{aggregate['wins']}/{aggregate['losses']}/{aggregate['ties']}; "
          f"pooled directional WR ex ties: {aggregate['win_rate_ex_ties']}")
    print("WARNING: Idealized historical direction only; no fees, payout, spread or slippage.")
    print(f"Private JSON report: {path}")
    return 0 if aggregate["markets_evaluated"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
