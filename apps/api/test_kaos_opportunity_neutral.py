import unittest
from datetime import datetime,timezone,timedelta
from kaos_opportunity import evaluate
NOW=datetime(2026,10,16,4,tzinfo=timezone.utc)

def obs(source,direction,age_days=0,observed_age_minutes=1):
    observed=NOW-timedelta(minutes=observed_age_minutes)
    published=observed-timedelta(days=age_days)
    return {'source':source,'direction':direction,'strength':1.,'event_id':source,
            'observed_at':observed.isoformat(),
            'published_at':published.isoformat(),'source_url':'https://example.com'}
class FusionTests(unittest.TestCase):
    def test_two_neutral_sources_not_trade_candidate(self):
        r=evaluate('AAPL',[obs('news','neutral'),obs('insider','neutral')],NOW)
        self.assertEqual(r['status'],'context_only')
        self.assertFalse(r['trade_recommendation'])
    def test_stale_publication_not_refreshed_by_polling(self):
        r=evaluate('AAPL',[obs('news','neutral',age_days=9)],NOW)
        self.assertEqual(r['evidence'],[])
    def test_two_independent_directional_sources(self):
        r=evaluate('AAPL',[obs('technical','bullish'),obs('options_flow','bullish')],NOW)
        self.assertEqual(r['status'],'research_candidate')
        self.assertFalse(r['trade_recommendation'])
    def test_only_one_directional_source_remains_unconfirmed(self):
        r=evaluate('AAPL',[obs('news','neutral'),obs('technical','bullish')],NOW)
        self.assertEqual(r['status'],'insufficient_confirmation')
if __name__=='__main__':unittest.main()
