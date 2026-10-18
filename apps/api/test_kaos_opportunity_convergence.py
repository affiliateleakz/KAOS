import unittest
from datetime import datetime,timezone,timedelta
from kaos_opportunity import evaluate
NOW=datetime(2026,10,16,5,tzinfo=timezone.utc)

def obs(source,direction,idx=0,age=2,strength=1):
    at=NOW-timedelta(minutes=age)
    return {'source':source,'direction':direction,'strength':strength,
            'event_id':f'{source}-{idx}', 'observed_at':at.isoformat(),
            'published_at':at.isoformat(),'source_url':'https://example.org/evidence'}

class Tests(unittest.TestCase):
    def test_spam_from_one_source_cannot_qualify(self):
        one=evaluate('GME',[obs('social','bullish',i) for i in range(100)],NOW)
        single=evaluate('GME',[obs('social','bullish')],NOW)
        self.assertEqual(one['score'],single['score'])
        self.assertEqual(one['status'],'insufficient_confirmation')
    def test_conflicting_sources_not_qualified(self):
        r=evaluate('GME',[obs('technical','bullish'),obs('options_flow','bearish')],NOW)
        self.assertEqual(r['bias'],'mixed')
        self.assertEqual(r['status'],'conflicting_evidence')
    def test_two_agreeing_categories(self):
        r=evaluate('GME',[obs('technical','bullish'),obs('options_flow','bullish')],NOW)
        self.assertEqual(r['status'],'research_candidate')
        self.assertEqual(r['confirming_directional_sources'],2)
    def test_neutral_cannot_confirm(self):
        r=evaluate('GME',[obs('news','neutral'),obs('social','neutral'),obs('filing','neutral')],NOW)
        self.assertEqual(r['status'],'context_only')
        self.assertEqual(r['confirming_directional_sources'],0)
    def test_future_event_rejected(self):
        r=evaluate('GME',[obs('news','neutral',age=-10)],NOW)
        self.assertEqual(r['evidence'],[])
    def test_limit_evidence_payload(self):
        r=evaluate('GME',[obs('news','neutral',i) for i in range(100)],NOW)
        self.assertEqual(len(r['evidence']),30)
        self.assertTrue(r['evidence_truncated'])

if __name__=='__main__':unittest.main()
