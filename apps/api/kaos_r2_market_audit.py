"""Read-only audit of the 20 configured KAOS Cloudflare candle markets.

Run on the active cPanel backend:
  cd ~/tradingwithkaos.com/backend
  /home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python apps/api/kaos_r2_market_audit.py

This reads archived candles only. It does not place trades, write R2,
train AI, log credentials or require an owner access token.
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

# Deployed app lives at ROOT/apps/api; credentials are at ROOT/.env.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from kaos_r2_archive import configured, read_archive, ArchiveUnavailable
from kaos_r2_research import inspect_history

MARKETS = [
    ("AAPL", "stock"), ("NVDA", "stock"), ("MSFT", "stock"),
    ("AMZN", "stock"), ("GOOGL", "stock"), ("META", "stock"),
    ("TSLA", "stock"), ("AMD", "stock"), ("PLTR", "stock"),
    ("COIN", "stock"), ("SPY", "etf"), ("QQQ", "etf"),
    ("BTC-USD", "crypto"), ("ETH-USD", "crypto"),
    ("SOL-USD", "crypto"), ("XRP-USD", "crypto"),
    ("DOGE-USD", "crypto"), ("ADA-USD", "crypto"),
    ("LINK-USD", "crypto"), ("AVAX-USD", "crypto"),
]

async def audit():
    if not configured():
        print("R2 NOT CONFIGURED; inspect the active backend environment")
        return 2
    semaphore = asyncio.Semaphore(3)
    now_ms = int(datetime.now(timezone.utc).timestamp()*1000)
    async def check(symbol, asset_class):
        async with semaphore:
            try:
                rows, source = await read_archive(symbol, asset_class, 60,
                                                  limit=300, now_ms=now_ms)
                history = inspect_history(rows, 60)
                status = "READABLE" if rows else "EMPTY"
                return (symbol, status, len(rows), history["gap_count"], source or "-")
            except (ArchiveUnavailable, ValueError, RuntimeError) as exc:
                return (symbol, "ERROR", 0, "-", type(exc).__name__)
    reports = await asyncio.gather(*(check(*market) for market in MARKETS))
    print("KAOS private R2 archive audit: 20 configured markets, 60s candles")
    print(f"{'MARKET':<12} {'STATUS':<10} {'BARS':>5} {'GAPS':>5} SOURCE")
    for market, status, bars, gaps, source in reports:
        print(f"{market:<12} {status:<10} {bars:>5} {str(gaps):>5} {source}")
    passed = sum(status == "READABLE" for _, status, *_ in reports)
    print(f"Readable markets: {passed}/{len(MARKETS)}")
    print("Counts are archive snapshots, not evidence of uninterrupted collection.")
    return 0 if passed == len(MARKETS) else 1

if __name__ == "__main__":
    raise SystemExit(asyncio.run(audit()))
