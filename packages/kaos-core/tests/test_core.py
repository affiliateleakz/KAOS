import unittest
from decimal import Decimal
from kaos.core import Bar,Signal,Quote,RiskGuard,PaperBroker,ENGINES
from kaos.memberships import Affiliate,calculate_referral_payouts,PERMISSIONS
class CoreTests(unittest.TestCase):
 def test_engine_registry(self):self.assertEqual(set(ENGINES),{'crypto','stock','options','forex','pocketoption'})
 def test_invalid_bar(self):
  with self.assertRaises(ValueError):Bar('',1,0,2,1)
 def test_risk_bad_stop(self):self.assertEqual(RiskGuard().qty('BUY',100,101),0)
 def test_risk_size(self):self.assertLessEqual(RiskGuard().qty('BUY',100,99)*100,1000)
 def test_no_duplicate(self):
  p=PaperBroker(RiskGuard());s=Signal('crypto','BTC','BUY','test',70,99,103)
  self.assertIsNotNone(p.enter(s,Quote(100,100)))
  self.assertIsNone(p.enter(s,Quote(100,100)))
 def test_fee_loss(self):
  p=PaperBroker(RiskGuard(),fee_bps=10,slippage_bps=0)
  p.enter(Signal('crypto','BTC','BUY','test',70,99,103),Quote(100,100))
  self.assertLess(p.exit('BTC',Quote(100,100))['pnl'],0)
 def test_kill(self):
  r=RiskGuard();r.settle(-201)
  self.assertEqual(r.qty('BUY',100,99),0)
 def test_options_fail_closed(self):self.assertIsNone(ENGINES['options'].signal('SPY',[]))
 def test_pocket_fail_closed(self):self.assertIsNone(ENGINES['pocketoption'].signal('EURUSD_otc',[]))
 def test_affiliate_mixed(self):
  m={'buyer':Affiliate('buyer','free','a'),'a':Affiliate('a','free','b'),'b':Affiliate('b','pro','c'),'c':Affiliate('c','ultimate')}
  out=calculate_referral_payouts(100,'buyer',m)
  self.assertEqual([x['amount'] for x in out],['10.00','15.00','5.00'])
 def test_ultimate_levels(self):
  m={'buyer':Affiliate('buyer','free','a'),'a':Affiliate('a','ultimate','b'),'b':Affiliate('b','ultimate','c'),'c':Affiliate('c','ultimate')}
  self.assertEqual(sum(Decimal(x['amount']) for x in calculate_referral_payouts(100,'buyer',m)),Decimal('80'))
 def test_pro_no_ai(self):self.assertNotIn('ai_execution',PERMISSIONS['pro'])
if __name__=='__main__':unittest.main()
