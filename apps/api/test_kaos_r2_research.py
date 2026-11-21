"""Regression tests: no synthetic fills, no gap-hiding in R2 historical replay."""
import os
import sys
import unittest
sys.path.insert(0,os.path.dirname(__file__))

from kaos_r2_research import inspect_history, structure_replay_from_archive

def candles(count=120, interval=60_000):
    return [{"ts":1_700_000_040_000+i*interval,
             "open":100.0 + i*.01,"high":101.0 + i*.01,
             "low":99.0 + i*.01,"close":100.5 + i*.01}
            for i in range(count)]

class TestArchiveReplay(unittest.TestCase):
    def test_empty_archive_never_generates_trades(self):
        result=structure_replay_from_archive([],60)
        self.assertEqual(result["status"],"insufficient_contiguous_history")
        self.assertIsNone(result["performance"])

    def test_gaps_block_replay_instead_of_cherry_picking_segment(self):
        rows=candles()
        for row in rows[60:]:
            row["ts"]+=7*60_000
        result=structure_replay_from_archive(rows,60)
        self.assertEqual(result["history"]["gap_count"],1)
        self.assertEqual(result["history"]["missing_intervals"],7)
        self.assertEqual(result["status"],"insufficient_contiguous_history")
        self.assertNotIn("summary",result)

    def test_continuous_archive_can_replay_research_only(self):
        result=structure_replay_from_archive(candles(),60)
        self.assertEqual(result["status"],"completed")
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["research_only"])
        self.assertIn("summary",result)

    def test_short_archive_is_not_scored(self):
        result=structure_replay_from_archive(candles(15),60)
        self.assertEqual(result["status"],"insufficient_contiguous_history")

    def test_invalid_or_duplicate_timestamps_rejected(self):
        rows=candles(30)
        rows[9]["ts"]=rows[8]["ts"]
        with self.assertRaises(ValueError):
            inspect_history(rows,60)

if __name__ == "__main__":
    unittest.main()
