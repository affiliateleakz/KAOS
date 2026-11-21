"""Offline regression checks for KAOS R2 batch research (no broker network)."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,os.path.dirname(__file__))
from kaos_r2_backtest_batch import collect_report, summarize_market, write_report

BASE = 1700000040000

def candles(count=130, gap=False):
    rows=[]
    for i in range(count):
        ts=BASE + i*60000 + (60000 if gap and i>=65 else 0)
        c=100 + i*.01
        rows.append({"ts":ts,"symbol":"BTC-USD","asset_class":"crypto",
                     "seconds":60,"source":"coinbase_exchange_public",
                     "open":c,"high":c+1,"low":c-1,"close":c+.5,"volume":1})
    return rows

class R2BatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_preserves_failures_and_disables_live_orders(self):
        async def reader(symbol, asset_class, seconds, *, limit, now_ms):
            if symbol=="FAIL":
                raise RuntimeError("upstream error")
            return candles(), "coinbase_exchange_public"
        report=await collect_report(
            markets=[("BTC-USD","crypto"),("FAIL","crypto")],
            reader=reader, now=datetime(2026,11,21,tzinfo=timezone.utc)
        )
        self.assertEqual(report["aggregate"]["markets_requested"],2)
        self.assertEqual(report["aggregate"]["markets_evaluated"],1)
        self.assertFalse(report["execution_enabled"])
        self.assertFalse(report["train_ai"])
        self.assertEqual(report["markets"][1]["status"],"read_or_validation_error")
        self.assertEqual(report["markets"][1]["error_type"],"RuntimeError")
        self.assertEqual(report["aggregate"]["trades_per_hour"],None)

    def test_gaps_block_entire_market_backtest(self):
        r=summarize_market("BTC-USD","crypto",candles(gap=True),"coinbase_exchange_public")
        self.assertEqual(r["status"],"insufficient_contiguous_history")
        self.assertIsNone(r["summary"])
        self.assertEqual(r["trades"],[])

    def test_short_history_does_not_produce_win_rate(self):
        r=summarize_market("BTC-USD","crypto",candles(count=15),"coinbase_exchange_public")
        self.assertEqual(r["status"],"insufficient_contiguous_history")
        self.assertIsNone(r["summary"])

    async def test_aggregate_empty_archive_does_not_invent_performance(self):
        async def reader(symbol, asset_class, seconds, *, limit, now_ms):
            return [],"coinbase_exchange_public"
        r=await collect_report(markets=[("BTC-USD","crypto")],reader=reader)
        self.assertEqual(r["aggregate"]["markets_evaluated"],0)
        self.assertIsNone(r["aggregate"]["win_rate_ex_ties"])
        self.assertEqual(r["aggregate"]["trades"],0)

    async def test_report_writes_private_file_without_overwriting(self):
        async def reader(symbol, asset_class, seconds, *, limit, now_ms):
            return candles(),"coinbase_exchange_public"
        report=await collect_report(markets=[("BTC-USD","crypto")],reader=reader,
                                    now=datetime(2026,11,21,tzinfo=timezone.utc))
        with tempfile.TemporaryDirectory() as directory:
            path=write_report(report,Path(directory)/"reports")
            data=json.loads(path.read_text())
            self.assertEqual(data["schema"],"kaos_r2_research_batch_v1")
            self.assertEqual(data["markets"][0]["symbol"],"BTC-USD")
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):
                write_report(report,Path(directory)/"reports")

if __name__=="__main__":
    unittest.main()
