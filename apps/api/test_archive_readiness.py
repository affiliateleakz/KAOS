import unittest
from datetime import datetime,timezone,timedelta
from kaos_archive_readiness import inspect_market
BASE=1761955200000
def bars(n=710):
    return [{"ts":BASE+i*60000,"seconds":60,"asset_class":"crypto",
            "symbol":"BTC-USD","source":"unit_test","open":100.0,
            "high":101.0,"low":99.0,"close":100.1,"volume":40} for i in range(n)]
def check(rows=None,evidence=None):
    return inspect_market(bars() if rows is None else rows,evidence or [],
        symbol="BTC-USD",asset_class="crypto",seconds=60,
        now_ms=BASE+800*60000)
class ReadinessTests(unittest.TestCase):
    def test_contiguous_market_classified_candidate_only(self):
        r=check()
        self.assertTrue(r["technical_research_ready"])
        self.assertFalse(r["model_accuracy_known"])
        self.assertFalse(r["multifactor_evidence_present"])
    def test_gap_blocks_long_contiguous_run(self):
        rows=bars()
        rows[350:]=[{**r,"ts":r["ts"]+60000*10} for r in rows[350:]]
        r=check(rows)
        self.assertGreater(r["gaps"],0)
        self.assertFalse(r["technical_research_ready"])
    def test_duplicate_detected(self):
        rows=bars();rows[-1]["ts"]=rows[-2]["ts"]
        self.assertEqual(check(rows)["duplicate_timestamps"],1)
        self.assertFalse(check(rows)["technical_research_ready"])
    def test_mixed_provider_not_trainable(self):
        rows=bars();rows[4]["source"]="another_feed"
        self.assertTrue(check(rows)["mixed_sources"])
        self.assertFalse(check(rows)["technical_research_ready"])
    def test_evidence_timestamp_coverage_not_faked(self):
        now=datetime.fromtimestamp((BASE+250*60000)/1000,timezone.utc)
        good={"asset":"BTC-USD","asset_class":"crypto","source":"news",
              "published_at":(now-timedelta(minutes=1)).isoformat(),
              "observed_at":now.isoformat()}
        future={**good,"source":"social","observed_at":
                  (now+timedelta(days=3)).isoformat()}
        r=check(evidence=[good,future])
        self.assertEqual(r["point_in_time_evidence_by_source"],{"news":1})
        self.assertEqual(r["future_observed_records"],1)
    def test_empty_archive_no_claims(self):
        r=check([])
        self.assertEqual(r["status"],"archive_not_ready")
        self.assertEqual(r["valid_closed_rows"],0)
        self.assertIsNone(r["last_closed_bar_ms"])
if __name__=="__main__":unittest.main()
