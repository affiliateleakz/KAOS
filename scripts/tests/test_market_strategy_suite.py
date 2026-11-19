"""Typed market routing, causal profiles, account-currency sizing and contract quotes."""
import sys,importlib.util
from pathlib import Path
import numpy as np,pandas as pd,pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('suite',ROOT/'research/kaos_market_suite_v1/strategies.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def daily_request(market='stocks'):
    dates=pd.bdate_range('2024-01-02',periods=300,tz='America/New_York');prices=100+np.arange(300)*.15;prices[-1]=prices[-2]-2
    bars=[{'ts':int((d+pd.Timedelta(hours=9,minutes=30)).timestamp()*1000),'end':int((d+pd.Timedelta(hours=16)).timestamp()*1000),'open':float(c+.1),'high':float(c+.5),'low':float(c-.5),'close':float(c)} for d,c in zip(dates,prices)]
    nxt=dates[-1]+pd.offsets.BDay(1);opening=int((nxt+pd.Timedelta(hours=9,minutes=30)).timestamp()*1000);now=opening+(20*60000 if market=='options' else 1000)
    return {'market':market,'symbol':'SPY','timeframe':'1d','contractType':s.CONTRACTS[market],'nowMs':now,'quote':{'symbol':'SPY','bid':float(prices[-1]+.1),'ask':float(prices[-1]+.2),'observedAt':now},'candles':bars,'context':{'hasPendingOrder':False,'hasOpenPosition':False,'consumedIntentIds':[],'sessionOpen':opening,'sessionClose':opening+int(6.5*s.HOUR),'previousSessionClose':bars[-1]['end']}}

def test_registry_exposes_five_separate_disabled_profiles():
    d=s.descriptors();assert {x['market'] for x in d}=={'stocks','forex','crypto','binary','options'}
    assert len({x['id'] for x in d})==5 and all(not x['executionEnabled'] and not x['productionApproved'] for x in d)

def test_account_currency_risk_and_portfolio_caps_skip_minimum_lots():
    kwargs={'equity':1000.,'risk_per_contract':100.,'notional_per_contract':1000.,'step':.01,'minimum':.1,'existing_planned_risk':0.,'existing_gross_notional':0.}
    assert s.size_contracts(**kwargs)==0.
    kwargs.update(equity=100000.,risk_per_contract=200.,notional_per_contract=10000.,step=1.,minimum=1.,existing_planned_risk=600.)
    assert s.size_contracts(**kwargs)==2.
    kwargs['existing_gross_notional']=99000.;assert s.size_contracts(**kwargs)==0.
    kwargs['risk_per_contract']=float('nan')
    with pytest.raises(ValueError):s.size_contracts(**kwargs)

def test_stock_profile_uses_daily_pullback_and_next_session_context():
    q=daily_request();r=s.evaluate(q)
    assert r['action']=='BUY' and r['stop']<r['entryReference'] and r['quantity'] is None and r['requiresBrokerAccountSizing']
    q['context']['consumedIntentIds']=[r['intentId']];assert s.evaluate(q)['reason']=='intent_already_consumed'

def test_stock_intraday_bars_cannot_masquerade_as_daily():
    q=daily_request();q['timeframe']='1m';assert s.evaluate(q)['action']=='HOLD'
    q['timeframe']='1d';q['candles'][-1]['end']=q['candles'][-1]['ts']+60000;assert s.evaluate(q)['action']=='HOLD'

def test_forming_stale_or_unverified_state_holds():
    q=daily_request();q['quote']['observedAt']-=30001;assert s.evaluate(q)['reason']=='stale_or_future_quote'
    q=daily_request();q['context'].pop('hasOpenPosition');assert s.evaluate(q)['reason']=='position_state_required'
    q=daily_request();q['candles'][-1]['end']=q['nowMs']+1;assert s.evaluate(q)['reason']=='invalid_or_forming_history'
    q=daily_request();q['context']['hasPendingOrder']=True;assert s.evaluate(q)['reason']=='pending_order_state_required'

def test_stop_quote_can_exit_even_without_warmup_history():
    q=daily_request();q['context'].update(hasOpenPosition=True,position={'profile':s.IDS['stocks'],'symbol':'SPY','entryAt':q['nowMs']-s.DAY,'side':1,'stop':200.});q['candles']=[]
    r=s.evaluate(q);assert r['action']=='EXIT' and r['reason']=='current_quote_stop'
    q['context']['consumedIntentIds']=[r['intentId']];assert s.evaluate(q)['reason']=='intent_already_consumed'

def test_foreign_profile_position_is_not_managed():
    q=daily_request();q['context'].update(hasOpenPosition=True,position={'profile':s.IDS['crypto'],'symbol':'BTCUSDT','entryAt':1,'side':1,'stop':200.})
    assert s.evaluate(q)['reason']=='position_profile_or_ledger_mismatch'

def london_frame(day):
    # Include three preceding days, full hourly quotes; test uses fixed causal features.
    start=pd.Timestamp(day,tz='Europe/London').tz_convert('UTC')-pd.Timedelta(days=3);rows=[]
    for i in range(80):
        t=start+pd.Timedelta(hours=i);rows.append({'ts':int(t.timestamp()*1000),'end':int((t+pd.Timedelta(hours=1)).timestamp()*1000),'open':100.,'high':101.,'low':99.,'close':100.,'atr':1.,'ema20':100.,'ema50':99.})
    f=pd.DataFrame(rows);last=len(f)-1;f.loc[last,['open','close','high']]=[100.,103.,104.]
    return f

def test_london_box_respects_winter_and_summer_dst():
    winter=london_frame('2026-01-06');summer=london_frame('2026-07-07')
    a=s.forex_setup(winter);b=s.forex_setup(summer)
    assert a and b and a['side']==b['side']==1
    assert pd.Timestamp(a['flattenAt'],unit='ms',tz='UTC').hour==16
    assert pd.Timestamp(b['flattenAt'],unit='ms',tz='UTC').hour==15

def test_london_box_rejects_missing_hour_and_later_repeat():
    f=london_frame('2026-07-07');assert s.forex_setup(f)
    missing=f.drop(f.index[-7]);assert s.forex_setup(missing) is None
    later=f.iloc[-1].copy();later['ts']+=s.HOUR;later['end']+=s.HOUR;later['close']=105.;later['high']=106.
    f=pd.concat([f,pd.DataFrame([later])],ignore_index=True);assert s.forex_setup(f) is None

def test_binary_direction_and_five_minute_expiry(monkeypatch):
    n=70;bars=[{'ts':i*60000,'end':(i+1)*60000,'open':100.,'high':101.,'low':99.,'close':100.} for i in range(n)];now=n*60000+1000
    q={'market':'binary','symbol':'EURUSD_otc','timeframe':'1m','contractType':'fixed_expiry','nowMs':now,'quote':{'symbol':'EURUSD_otc','price':100.,'payout':.8,'observedAt':now},'candles':bars,'context':{'hasPendingOrder':False,'hasOpenPosition':False,'consumedIntentIds':[],'broker':'pocket_option'}}
    monkeypatch.setattr(s,'binary_signals',lambda f:np.ones(len(f),dtype=int));r=s.evaluate(q)
    assert r['action']=='CALL' and r['expiresAt']==now+300000 and 'stop' not in r and 'target' not in r
    q['quote']['payout']=.7;assert s.evaluate(q)['action']=='HOLD'

def option_chain(symbol,now):
    return [{'symbol':'LONG','underlying':symbol,'right':'CALL','strike':140.,'delta':.5,'bid':3.9,'ask':4.,'openInterest':200,'multiplier':100.,'observedAt':now,'expiry':now+45*s.DAY},{'symbol':'SHORT','underlying':symbol,'right':'CALL','strike':150.,'delta':.3,'bid':1.,'ask':1.05,'openInterest':200,'multiplier':100.,'observedAt':now,'expiry':now+45*s.DAY}]

def test_options_missing_chain_holds_and_fresh_chain_prices_debit():
    q=daily_request('options');assert s.evaluate(q)['reason']=='historical_and_current_option_contract_data_required'
    q['optionChain']=option_chain('SPY',q['nowMs']);r=s.evaluate(q)
    assert r['action']=='BULL_CALL_SPREAD' and r['debitPerUnderlyingUnit']==3. and r['riskPerSpread']==302.6 and not r['historicalOptionPnLValidated']
    q['optionChain'][1]['multiplier']=10.;assert s.evaluate(q)['action']=='HOLD'

def test_options_stale_wide_or_expiry_mismatch_rejected():
    now=100*s.DAY;chain=option_chain('SPY',now)
    chain[0]['observedAt']-=30001;assert s.spread_candidate(chain,'SPY',140.,now) is None
    chain=option_chain('SPY',now);chain[1]['expiry']+=s.DAY;assert s.spread_candidate(chain,'SPY',140.,now) is None
    chain=option_chain('SPY',now);chain[0]['bid']=1.;assert s.spread_candidate(chain,'SPY',140.,now) is None

def test_spread_exit_uses_bid_for_long_and_ask_for_short():
    now=100*s.DAY;chain=option_chain('SPY',now);p={'longContract':'LONG','shortContract':'SHORT','expiry':now+20*s.DAY,'multiplier':100.,'entryCostPerSpread':301.3,'riskPerSpread':302.6,'maxProfitPerSpread':697.4}
    for leg in chain:leg['expiry']=p['expiry']
    r=s.manage_spread({'symbol':'SPY','action':'HOLD','executionEnabled':False},chain,p,None,now)
    assert r['action']=='EXIT_SPREAD' and r['reason']=='option_time_exit'
    assert r['estimatedCreditAfterExitCommission']==pytest.approx((3.9-1.05)*100-1.3)
    assert not r['fillGuaranteed']

def test_crypto_profile_matches_previous_frozen_entry():
    c=100+np.arange(300)*.1;bars=[{'ts':i*4*s.HOUR,'end':(i+1)*4*s.HOUR,'open':float(v-.1),'high':float(v+.2),'low':float(v-.2),'close':float(v)} for i,v in enumerate(c)]
    bars[-1].update(close=float(c[-1]+1),high=float(c[-1]+1.2),open=float(c[-1]))
    f=s.crypto_features(bars)
    assert s.crypto_entry(f)
    assert s.crypto_entry(f)==bool(s.SWING.prior.spot_signals(f,'breakout20')[-1])


def test_quote_instrument_mismatch_is_blocked():
    q=daily_request();q['quote']['symbol']='AAPL'
    assert s.evaluate(q)['reason']=='quote_instrument_mismatch'


def test_forex_alias_normalization_and_once_per_session():
    f=london_frame('2026-07-07');now=int(f.end.iloc[-1])+1000
    q={'market':'forex','symbol':'EURUSD=X','timeframe':'1h','contractType':'spot_fx','nowMs':now,'quote':{'symbol':'EURUSD','bid':103.,'ask':103.01,'observedAt':now},'candles':f[['ts','end','open','high','low','close']].to_dict('records'),'context':{'hasPendingOrder':False,'hasOpenPosition':False,'consumedIntentIds':[],'sessionAlreadyTraded':False}}
    r=s.evaluate(q);assert r['action']=='BUY' and r['symbol']=='EURUSD' and r['stop']<r['entryReference']<r['target']
    q['context']['sessionAlreadyTraded']=True;assert s.evaluate(q)['reason']=='already_traded_london_date'


def test_binary_actual_conditions_are_mirrored():
    n=70;f=pd.DataFrame({'ema20':np.full(n,101.),'ema50':np.linspace(99.,100.,n),'low':np.full(n,99.),'high':np.full(n,103.),'close':np.full(n,102.),'open':np.full(n,101.),'rsi':np.full(n,55.),'atr':np.ones(n)})
    f.loc[n-1,['close','open','high']]=[104.,103.,105.]
    assert s.binary_signals(f)[-1]==1
    f.ema20=99.;f.ema50=np.linspace(102.,100.,n);f.rsi=45.;f.low=97.;f.loc[n-1,['close','open','low']]=[96.,97.,95.]
    assert s.binary_signals(f)[-1]==-1


def test_stock_after_hours_stop_is_scheduled_not_fictionally_filled():
    q=daily_request();now=q['candles'][-1]['end']+1000;q['nowMs']=now;q['quote']['observedAt']=now
    q['context'].update(hasOpenPosition=True,position={'profile':s.IDS['stocks'],'symbol':'SPY','entryAt':now-s.DAY,'side':1,'stop':200.});q['candles']=[]
    r=s.evaluate(q);assert r['action']=='SCHEDULE_EXIT_NEXT_OPEN' and 'observedExitQuote' not in r


def test_cli_labels_replay_and_uses_actual_clock_by_default(tmp_path):
    import json,subprocess
    path=tmp_path/'fixture.json';path.write_text(json.dumps(daily_request()))
    command=[sys.executable,str(ROOT/'scripts/evaluate_market_strategy.py'),'--input',str(path)]
    replay=json.loads(subprocess.run(command+['--replay'],check=True,capture_output=True,text=True).stdout)
    assert replay['mode']=='historical_replay' and replay['action']=='BUY' and not replay['eligibleForPerformanceClaims']
    current=json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)
    assert current['mode']=='current_clock_paper_intent' and current['action']=='HOLD' and current['reason']=='stale_or_future_quote'
