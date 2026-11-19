"""KAOS Micro Reversion research predictor. Produces paper signals, never orders."""
import importlib.util
import json
import math
from pathlib import Path
import sys
from xgboost import XGBClassifier

ROOT=Path(__file__).resolve().parents[2]
_spec=importlib.util.spec_from_file_location('kaos_research_features',ROOT/'scripts/research_broker_edge.py')
_features=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_features)


class ResearchStrategy:
    symbols={'BTCUSDT','ETHUSDT','SOLUSDT'}

    def __init__(self):
        self.model=XGBClassifier()
        self.model.load_model(Path(__file__).parent/'audit/selected_model.json')

    def predict(self,symbol,candles,as_of_ms):
        result={'strategy':'KAOS Micro Reversion Research v1','direction':'HOLD','expirySeconds':15,
                'researchOnly':True,'executionEnabled':False,'liveApproved':False}
        if symbol not in self.symbols:return {**result,'reason':'Unsupported research market; not a Pocket Option model'}
        rows=[];previous=None
        for bar in candles:
            ts=int(bar['ts']);end=int(bar.get('closeTs',ts+5000))
            if ts%5000 or end!=ts+5000 or previous is not None and ts<=previous:raise ValueError('Require sorted, unique completed five-second bars')
            if end>as_of_ms:break
            values=[float(bar[k]) for k in ('open','high','low','close')];o,h,l,c=values
            if not all(math.isfinite(v) and v>0 for v in values) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid OHLC')
            if previous is not None and ts!=previous+5000:rows=[]
            rows.append((ts,*values));previous=ts
        if len(rows)<320:return {**result,'reason':'Need at least 320 contiguous completed five-second candles'}
        if as_of_ms-(rows[-1][0]+5000)>5000:return {**result,'reason':'Stale candle context'}
        matrix=_features.features([(symbol,rows)])[_features.FEATURES].iloc[[-1]]
        probability=float(self.model.predict_proba(matrix)[0,1])
        direction='BUY' if probability>=.6 else 'SELL' if probability<=.4 else 'HOLD'
        return {**result,'direction':direction,'probUp':probability,'modelScore':max(probability,1-probability),
                'reason':'Experimental score threshold; uncalibrated probability, failed adverse-fill gate',
                'decisionAt':rows[-1][0]+5000}


if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(ResearchStrategy().predict(data['symbol'],data['candles'],data['asOfMs']),indent=2))
