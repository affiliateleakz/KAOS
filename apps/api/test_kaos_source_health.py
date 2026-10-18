import unittest
from datetime import datetime, timedelta, timezone
from kaos_source_health import provider, summarize_health

NOW = datetime(2026, 10, 16, 17, 0, tzinfo=timezone.utc)

def record(event, source, klass, minutes):
    return {'event_id':event,'source':source,'asset_class':klass,
            'observed_at':(NOW-timedelta(minutes=minutes)).isoformat()}

class HealthTests(unittest.TestCase):
    def test_recent_and_stale(self):
        rows=[record('alpaca:iex:AAPL:1','technical','stock',10),
              record('tradier:0:AAPL:1','options_flow','option',180),
              record('binance-spot:BTC:1','technical','crypto',15)]
        result=summarize_health(rows,NOW)
        self.assertEqual(result['sample_observations'],3)
        states={(x['provider'],x['asset_class']):x['state'] for x in result['sources']}
        self.assertEqual(states[('alpaca','stock')],'recent_observation')
        self.assertEqual(states[('tradier','option')],'stale_or_market_closed')
        self.assertFalse(result['feed_guarantees'])
    def test_grouping_and_unknown(self):
        rows=[record('unknown:abc','news','stock',30),record('unknown:def','news','stock',20)]
        result=summarize_health(rows,NOW)
        self.assertEqual(len(result['sources']),1)
        self.assertEqual(result['sources'][0]['provider'],'other')
        self.assertEqual(result['sources'][0]['observations_in_sample'],2)
        self.assertEqual(provider('dexscreener:solana:xxx'),'dexscreener')
    def test_13f_and_social_provider_tags(self):
        self.assertEqual(provider('sec13f:0000320193:xxx:037833100:0'),'sec13f')
        self.assertEqual(provider('bsky-social:GME:2026101604'),'bsky-social')
        rows=[record('sec13f:0000320193:xxx:037833100:0','institutional','stock',500),
              record('bsky-social:GME:2026101604','social','stock',10)]
        r=summarize_health(rows,NOW)
        self.assertEqual({x['provider'] for x in r['sources']},{'sec13f','bsky-social'})
    def test_no_data(self):
        self.assertEqual(summarize_health([],NOW)['sources'],[])
if __name__=='__main__': unittest.main()
