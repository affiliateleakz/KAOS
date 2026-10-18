import unittest
from datetime import datetime,timezone
from kaos_source_health import provider,summarize_health

class ActivityHealthTest(unittest.TestCase):
    def test_option_provider_name(self):
        self.assertEqual(provider('option-volume-rise:0:SPY261016C00500000:123456'), 'option-volume-rise')
    def test_records_stay_research_only(self):
        now=datetime(2026,10,16,15,30,tzinfo=timezone.utc)
        health=summarize_health([{'source':'options_flow','asset_class':'option',
            'event_id':'option-volume-rise:0:SPY261016C00500000:123456',
            'observed_at':now.isoformat()}],now=now)
        self.assertEqual(health['sources'][0]['provider'],'option-volume-rise')
        self.assertEqual(health['sources'][0]['state'],'recent_observation')
if __name__=='__main__':unittest.main()
