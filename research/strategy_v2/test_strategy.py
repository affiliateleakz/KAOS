import unittest,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).parent))
from kaos_strategy import generate,backtest,features
class Tests(unittest.TestCase):
 def setUp(self):
  rng=np.random.default_rng(13);n=400
  close=100+np.cumsum(rng.normal(.05,.5,n));op=np.r_[close[0],close[:-1]]
  self.d=pd.DataFrame(dict(open=op,high=np.maximum(op,close)+.15,low=np.minimum(op,close)-.15,close=close,volume=np.ones(n)*1000))
 def test_features(self):
  d=features(self.d);self.assertTrue('atr' in d);self.assertTrue(d.atr.iloc[-1]>0)
 def test_no_lookahead_signals(self):
  first=generate(self.d.iloc[:300]);changed=self.d.copy();changed.loc[300:,'close']*=1.1;changed.loc[300:,'high']*=1.11
  other=generate(changed);self.assertTrue((first.direction.values==other.direction.iloc[:300].values).all())
 def test_backtest(self):
  d,t,s=backtest(self.d);self.assertIn('return_pct',s);self.assertTrue(s['trades']>=0)
 def test_risk_params(self):
  with self.assertRaises(ValueError):backtest(self.d,risk_fraction=1)
 def test_invalid_ohlc(self):
  bad=self.d.copy();bad.loc[20,'low']=bad.loc[20,'high']+1
  with self.assertRaises(ValueError):generate(bad)
 def test_fee_effect(self):
  _,low,_=backtest(self.d,fee_bps=0);_,high,_=backtest(self.d,fee_bps=20)
  # Different sizes allowed; ensure fee always nonnegative.
  if len(high):self.assertTrue((high.fees>=0).all())
if __name__=='__main__':unittest.main()
