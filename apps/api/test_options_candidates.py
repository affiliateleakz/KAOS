import unittest
from datetime import datetime,timezone
from kaos_options_candidates import screen
ASOF=datetime(2026,11,20,12,tzinfo=timezone.utc)
def contract(symbol="AAPL261127C00200000",right="call",bid=2,ask=2.1,volume=300,oi=1300):
    return {"symbol":symbol,"option_type":right,"bid":bid,"ask":ask,
            "strike":200,"volume":volume,"open_interest":oi}
class CandidateTests(unittest.TestCase):
    def test_real_expiration_and_no_recommendation(self):
        r=screen("AAPL","2026-11-27",[contract()],asof=ASOF,bias="bullish")
        self.assertEqual(r["candidates"][0]["right"],"CALL")
        self.assertTrue(r["candidates"][0]["matches_technical_bias"])
        self.assertEqual(r["call_put_recommendation"],"NONE")
        self.assertIsNone(r["recommended_expiration"])
        self.assertFalse(r["validated_forecast"])
    def test_illiquid_and_invalid_quotes_filtered(self):
        data=[contract(bid=1,ask=2),contract(volume=0),contract(oi=2),
              contract(symbol="AAPL261127P00200000",right="put")]
        r=screen("AAPL","2026-11-27",data,asof=ASOF)
        self.assertEqual(r["eligible_contract_count"],1)
        self.assertIsNone(r["candidates"][0]["matches_technical_bias"])
    def test_expired_chain_rejected(self):
        with self.assertRaisesRegex(ValueError,"Expired"):
            screen("AAPL","2026-11-19",[contract()],asof=ASOF)
    def test_empty_chain_is_not_a_call_put(self):
        r=screen("AAPL","2026-11-27",[],asof=ASOF)
        self.assertEqual(r["status"],"no_eligible_contracts")
        self.assertEqual(r["candidates"],[])
    def test_sandbox_flag_transparency(self):
        r=screen("AAPL","2026-11-27",[contract()],asof=ASOF,sandbox=True)
        self.assertEqual(r["environment"],"sandbox_delayed")
    def test_no_fake_greeks_or_accuracies(self):
        r=screen("AAPL","2026-11-27",[contract()],asof=ASOF)
        x=r["candidates"][0]
        self.assertNotIn("delta",x)
        self.assertNotIn("win_probability",x)
if __name__=="__main__":unittest.main()
