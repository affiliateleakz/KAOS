"""No-network tests for the manually invoked KAOS backfill command."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from kaos_backfill import backfill, main

START=1761955200000
def candles(n=80):
    return [{"timestamp":datetime.fromtimestamp((START+i*60000)/1000,timezone.utc).isoformat(),
             "open":100+i*.1,"high":101+i*.1,
             "low":99+i*.1,"close":100.2+i*.1,"volume":50+i}
            for i in range(n)]

class BackfillTests(unittest.TestCase):
    def test_ai_compatible_export(self):
        doc=backfill(candles(),symbol="BTCUSDT",exchange="BINANCE",
                     asset_class="crypto",seconds=60,
                     observed_at_ms=START+81*60000)
        self.assertEqual(doc["format_version"],"kaos_research_ohlcv_v1")
        self.assertTrue(doc["usable_for_training"])
        self.assertEqual(doc["closed_bar_count"],80)
        self.assertEqual(len(doc["candles"]),80)
        self.assertTrue(all(x["source"]=="tradingview_unofficial" for x in doc["candles"]))

    def test_gaps_not_training_ready(self):
        rows=candles()
        rows.pop(15)
        doc=backfill(rows,symbol="BTCUSDT",exchange="BINANCE",
                     asset_class="crypto",seconds=60,
                     observed_at_ms=START+81*60000)
        self.assertEqual(doc["noncontiguous_intervals"],1)
        self.assertFalse(doc["usable_for_training"])

    def test_manual_command_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            inp=Path(root)/"source.json"
            out=Path(root)/"export.json"
            inp.write_text(json.dumps({"records":candles()}))
            args=["--input-json",str(inp),"--symbol","BTCUSDT",
                  "--exchange","BINANCE","--asset-class","crypto",
                  "--seconds","60","--output",str(out)]
            main(args)
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text())["closed_bar_count"],80)
            with self.assertRaises(SystemExit):
                main(args)

    def test_fetch_requires_terms(self):
        with tempfile.TemporaryDirectory() as root:
            args=["--fetch","--symbol","BTCUSDT","--exchange","BINANCE",
                  "--asset-class","crypto","--output",str(Path(root)/"out.json")]
            with self.assertRaises(SystemExit):
                main(args)

    def test_no_second_bars(self):
        with tempfile.TemporaryDirectory() as root:
            args=["--input-json","fixture.json","--symbol","BTCUSDT",
                  "--exchange","BINANCE","--asset-class","crypto",
                  "--seconds","5","--output",str(Path(root)/"out.json")]
            with self.assertRaises(SystemExit):
                main(args)

if __name__=="__main__":
    unittest.main()
