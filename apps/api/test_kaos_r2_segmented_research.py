"""No cherry-picking / no fabricated candles across R2 archive gaps."""
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(__file__))
from kaos_r2_segmented_research import gap_aware_replay

def rows(n, start=1700000040000):
    out=[]
    for i in range(n):
        p=100+(i%8)*0.2
        out.append({"ts":start+i*60000,"open":p,"high":p+1,
                    "low":p-1,"close":p+0.1})
    return out

class GapAwareTests(unittest.TestCase):
    def test_evaluates_both_sides_of_gap_without_cross_gap_trades(self):
        a=rows(90)
        b=rows(90,start=a[-1]["ts"]+11*60000)
        report=gap_aware_replay(a+b,60,expiry_bars=4,lookback=12)
        self.assertEqual(report["status"],"completed")
        self.assertEqual(report["history"]["eligible_segments"],2)
        self.assertEqual(report["history"]["gap_count"],1)
        self.assertEqual(report["history"]["missing_intervals"],10)
        self.assertEqual(report["history"]["eligible_fraction"],1)
        boundary=a[-1]["ts"]
        for trade in report["trades"]:
            self.assertTrue(trade["exit_ts"]<=boundary or trade["entry_ts"]>boundary)

    def test_short_fragments_are_reported_not_tested(self):
        a=rows(10)
        b=rows(80,start=a[-1]["ts"]+4*60000)
        report=gap_aware_replay(a+b,60,expiry_bars=4,lookback=12)
        self.assertEqual(report["history"]["skipped_bars"],10)
        self.assertEqual(report["history"]["eligible_bars"],80)
        self.assertEqual(report["history"]["eligible_fraction"],round(80/90,4))
        self.assertEqual(report["history"]["eligible_segments"],1)

    def test_all_segments_too_short_no_statistics(self):
        a=rows(10)
        b=rows(10,start=a[-1]["ts"]+4*60000)
        report=gap_aware_replay(a+b,60,expiry_bars=4,lookback=12)
        self.assertEqual(report["status"],"insufficient_contiguous_history")
        self.assertEqual(report["trades"],[])
        self.assertIsNone(report["summary"])

if __name__=="__main__":
    unittest.main()
