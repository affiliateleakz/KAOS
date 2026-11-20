"""Synthetic-only point-in-time evidence tests."""
import unittest
from datetime import datetime,timezone,timedelta
from kaos_point_in_time import available_evidence,fixed_fusion

T=datetime(2026,11,20,12,tzinfo=timezone.utc)
TS=int(T.timestamp()*1000)
def obs(source="news",direction="bullish",seen=None,published=None,event="e1"):
    return {"asset":"AAPL","asset_class":"stock","source":source,
            "direction":direction,"strength":.8,"event_id":event,
            "observed_at":(seen or T).isoformat(),
            "published_at":(published or T).isoformat()}

class PointInTimeTests(unittest.TestCase):
    def eligible(self,items):
        return available_evidence(items,as_of_ms=TS,symbol="AAPL",asset_class="stock")
    def test_future_discovered_article_excluded_even_if_published_earlier(self):
        e,reject=self.eligible([obs(seen=T+timedelta(hours=1),
                                    published=T-timedelta(hours=2))])
        self.assertEqual(e,[])
        self.assertEqual(reject["future_or_missing_observation_time"],1)
    def test_future_publication_excluded(self):
        e,reject=self.eligible([obs(published=T+timedelta(minutes=1))])
        self.assertEqual(e,[])
        self.assertEqual(reject["invalid_publication_time"],1)
    def test_naive_time_fails_closed(self):
        raw=obs();raw["observed_at"]="2026-11-20T12:00:00"
        e,_=self.eligible([raw])
        self.assertEqual(e,[])
    def test_wrong_stock_excluded(self):
        raw=obs();raw["asset"]="MSFT"
        e,_=self.eligible([raw])
        self.assertEqual(e,[])
    def test_same_category_not_counted_as_independent(self):
        a,b=obs(event="a"),obs(event="b")
        e,_=self.eligible([a,b])
        self.assertEqual(fixed_fusion({"buy_sell":"RESEARCH_BULLISH"},e),"WAIT")
    def test_two_independent_sources_can_confirm(self):
        e,_=self.eligible([obs("news",event="a"),obs("social",event="b")])
        self.assertEqual(fixed_fusion({"buy_sell":"RESEARCH_BULLISH"},e),"RESEARCH_BULLISH")
    def test_conflict_causes_wait(self):
        e,_=self.eligible([obs("news",event="a"),obs("social",event="b"),
                            obs("insider",direction="bearish",event="c")])
        self.assertEqual(fixed_fusion({"buy_sell":"RESEARCH_BULLISH"},e),"WAIT")
    def test_future_social_does_not_affect_earlier_decision(self):
        before=[obs("news",event="a"),obs("social",event="b")]
        after=before+[obs("filing",direction="bearish",event="c",
                           seen=T+timedelta(days=1),published=T)]
        a,_=self.eligible(before);b,_=self.eligible(after)
        self.assertEqual(fixed_fusion({"buy_sell":"RESEARCH_BULLISH"},a),
                         fixed_fusion({"buy_sell":"RESEARCH_BULLISH"},b))
if __name__=="__main__":unittest.main()
