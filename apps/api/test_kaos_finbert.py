import unittest
from kaos_finbert import score_headline, normalize

def fake(*args, **kwargs):
    return [{'label':'positive','score':.7},{'label':'negative','score':.1},{'label':'neutral','score':.2}]

class FinbertTests(unittest.TestCase):
    def test_positive(self):
        r=score_headline('Earnings beat', '2026-10-14T12:00:00Z','2026-10-14T12:01:00Z','BTC-USD',fake)
        self.assertEqual(r['sentiment'],'positive')
        self.assertFalse(r['trade_authorized'])
    def test_deterministic(self):
        a=score_headline('X','2026-10-14T12:00:00Z','2026-10-14T12:01:00Z','A',fake)
        b=score_headline('X','2026-10-14T12:00:00Z','2026-10-14T12:02:00Z','A',fake)
        self.assertEqual(a['event_id'],b['event_id'])
    def test_future_news_rejected(self):
        with self.assertRaises(ValueError): score_headline('X','2026-10-14T12:02:00Z','2026-10-14T12:01:00Z','A',fake)
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError): score_headline('X','2026-10-14T12:00:00','2026-10-14T12:01:00Z','A',fake)
    def test_invalid_probs(self):
        with self.assertRaises(ValueError): normalize([{'label':'positive','score':1}])
    def test_empty_headline(self):
        with self.assertRaises(ValueError): score_headline(' ','2026-10-14T12:00:00Z','2026-10-14T12:01:00Z','A',fake)
if __name__=='__main__': unittest.main()
