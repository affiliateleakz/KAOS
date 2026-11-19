"""Causal signals, realistic session semantics and fixed-expiry separation."""
import sys,importlib.util
from pathlib import Path
import numpy as np,pandas as pd,pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('pulse2',ROOT/'research/kaos_pulse_v2/strategy.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
import pulse_v2_replay as r
H=3600000

def frame(n=260):
    c=100+np.sin(np.arange(n)/4)
    return pd.DataFrame({'ts':np.arange(n)*H,'end':(np.arange(n)+1)*H,'open':c-.1,'high':c+1,'low':c-1,'close':c})

def setup(n=260):
    f=frame(n)
    for col,value in {'er':.2,'z':0.,'z_slow':0.,'rsi':50.,'bb_low':99.,'bb_high':101.,'ema200':90.,'ema50':95.,'atr':1.}.items():f[col]=value
    f.loc[n-2,['z','z_slow','rsi','close']]=[-1.5,-1.,30.,98.]
    f.loc[n-1,['open','close','rsi']]=[99.,100.,40.]
    return f

def test_wilder_rsi_extremes_and_flat_case():
    for direction,expected in [(1,100),(-1,0),(0,50)]:
        f=frame();f.close=100+direction*np.arange(len(f))*.1;f.open=f.close;f.high=f.close+1;f.low=f.close-1
        out=v.indicators(f);assert out.rsi.iloc[-1]==pytest.approx(expected)
    assert v.wilder([2,4,6,8],3)[2]==4

def test_indicator_prefix_causal():
    f=frame(400);a=v.indicators(f.iloc[:300]);f.loc[300:,'close']+=50;b=v.indicators(f)
    for col in ['atr','rsi','er','bb_low','ema200']:np.testing.assert_allclose(a[col],b[col].iloc[:300],equal_nan=True)

def test_reclaim_required_and_trend_guard_honored():
    f=setup();assert v.signals(f,True)[-1]==1
    f.loc[len(f)-1,'close']=98.;assert v.signals(f)[-1]==0
    f=setup();f.ema200=105.;assert v.signals(f,False)[-1]==1 and v.signals(f,True)[-1]==0

def test_short_mirror_only_when_explicitly_enabled():
    f=setup();f.loc[len(f)-2,['z','z_slow','rsi','close']]=[1.5,1.,70.,102.];f.loc[len(f)-1,['open','close','rsi']]=[101.,100.,65.]
    assert v.signals(f,False,True)[-1]==-1 and v.signals(f,False,False)[-1]==0

def test_cost_guard_rejects_tiny_target():
    assert not v.cost_budget(.01,100,3,10,2)
    assert v.cost_budget(1,100,3,10,2)
    assert not v.cost_budget(float('nan'),100,3,10,2)

def test_risk_sizing_never_rounds_up_to_minimum_lot():
    assert v.risk_quantity(100,100,90,lot_step=1,min_lot=1)==0
    qty=v.risk_quantity(10000,100,90,lot_step=.01,min_lot=.01)
    per_unit=100*1.0002-90*.9998+.001*(100*1.0002+90*.9998)
    assert qty*per_unit<=50+1e-9 and qty*100*1.0002*1.001<=10000+1e-9

def test_paper_guards_and_quote_anchored_bracket(monkeypatch):
    f=frame();bars=f[['ts','open','high','low','close']].to_numpy();now=int(f.end.iloc[-1]);quote={'bid':109.,'ask':110.,'observedAt':now}
    assert v.paper_intent('BTCUSDT',bars,3600,now+180000,quote)['action']=='HOLD'
    monkeypatch.setattr(v,'signals',lambda f,trend_guard:np.ones(len(f),dtype=int))
    original=v.indicators
    def fixed(bars):
        out=original(bars);out.atr=1.;return out
    monkeypatch.setattr(v,'indicators',fixed)
    intent=v.paper_intent('BTCUSDT',bars,3600,now,quote)
    assert intent['action']=='BUY' and intent['stop']==108. and intent['target']==113. and not intent['executionEnabled']
    with pytest.raises(ValueError):v.paper_intent('BTCUSDT',bars,3600,float('nan'),quote)

def basebars(n=35):return [{'ts':i*H,'end':(i+1)*H,'open':100.,'high':101.,'low':99.,'close':100.,'session_start':None,'session_end':None} for i in range(n)]

def test_bracket_ambiguity_stops_first_and_target_gap_is_capped():
    b=basebars();b[1].update(high=110.,low=90.);f=pd.DataFrame(b);sig=np.zeros(len(f),dtype=int);sig[0]=1
    out=r.brackets('BTC',b,f,sig,np.ones(len(f)),3,2,(0,100*H),'crypto')
    assert out[0]['reason']=='stop' and out[0]['exitPrice']==pytest.approx(98*.9998)
    b[1].update(open=100.,high=101.,low=99.);b[2].update(open=105.,high=110.,low=90.)
    out=r.brackets('BTC',b,f,sig,np.ones(len(f)),3,2,(0,100*H),'crypto')
    assert out[0]['reason']=='target' and out[0]['exitPrice']==pytest.approx(103*.9998)

def test_dividend_credit_requires_hold_before_ex_date():
    b=basebars();f=pd.DataFrame(b);sig=np.zeros(len(f),dtype=int);sig[0]=1
    out=r.brackets('ETF',b,f,sig,np.ones(len(f)),3,2,(0,100*H),'stocks',dividends=[{'ts':2*H,'amount':1.},{'ts':H,'amount':10.}])
    assert out[0]['grossDividendsPerUnit']==1.

def test_session_groups_preserve_short_close_without_fabrication():
    start=int(9.5*H);end=16*H;b=[]
    for i in range(7):b.append({'ts':start+i*H,'end':min(start+(i+1)*H,end),'open':100.,'high':101.,'low':99.,'close':100.,'session_start':start,'session_end':end})
    f=r.requested(b,14400,'stocks');assert len(f)==2 and f.end.iloc[-1]-f.ts.iloc[-1]==int(2.5*H)
    f=r.requested([x for i,x in enumerate(b) if i!=1],14400,'stocks');assert len(f)==1

def test_unscheduled_crypto_gap_resets_but_known_stock_close_does_not():
    b=basebars();assert len(r.parts([b[0],b[2]],'crypto'))==2
    a={**b[0],'session_start':0,'session_end':H};c={**b[2],'session_start':2*H,'session_end':3*H};assert len(r.parts([a,c],'stocks'))==1

def test_binary_is_fixed_expiry_and_combines_delay_adverse_quote():
    a=np.column_stack((np.arange(100)*5000,np.full((100,4),100.)));a[24,1]=101.
    f=pd.DataFrame({'ts':[0],'end':[60000]});sig=np.array([1]);out=r.binary('PO',a,f,sig,1,(0,999999));stress=r.binary('PO',a,f,sig,1,(0,999999),True)
    assert out[0]['outcome']==1 and stress[0]['outcome']==-1
    assert stress[0]['exit']-stress[0]['entry']==60000


def test_forex_weekend_is_not_an_arbitrary_midweek_gap():
    friday=int(pd.Timestamp('2026-10-02 21:00',tz='UTC').timestamp()*1000);sunday=int(pd.Timestamp('2026-10-04 22:00',tz='UTC').timestamp()*1000)
    a=basebars(1)[0];a.update(ts=friday,end=friday+H);b={**a,'ts':sunday,'end':sunday+H}
    assert len(r.parts([a,b],'forex'))==1
    a={**a,'ts':friday-3*86400000,'end':friday-3*86400000+H};b={**b,'ts':sunday-3*86400000,'end':sunday-3*86400000+H}
    assert len(r.parts([a,b],'forex'))==2


def test_split_crossing_trade_is_not_scored():
    b=basebars();f=pd.DataFrame(b);sig=np.zeros(len(f),dtype=int);sig[0]=1
    assert r.brackets('BTC',b,f,sig,np.ones(len(f)),3,2,(0,20*H),'crypto')==[]


def test_duplicate_and_overlapping_quotes_are_rejected():
    b=basebars(3)
    with pytest.raises(ValueError,match='Duplicate'):r.parts([b[0],b[0]],'crypto')
    b[0]['end']=2*H
    with pytest.raises(ValueError,match='Overlapping'):r.parts(b,'crypto')


def test_cost_sizing_rejects_unreasonable_fill_inputs():
    with pytest.raises(ValueError):v.risk_quantity(1000,100,90,slip_bps=10001)
