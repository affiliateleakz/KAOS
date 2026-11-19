"""Five separate research profiles. Signals/intents only; no broker/order interface."""
import hashlib,importlib.util,json,math
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
DAILY=load('suite_daily',ROOT/'daily_edge_v1/strategy.py')
SWING=load('suite_swing',ROOT/'kaos_swing_v1/strategy.py')
TECH=load('suite_technical',ROOT/'kaos_pulse_v2/strategy.py')
HOUR=3600000;DAY=86400000
IDS={'stocks':'kaos_stocks_pullback_v1','forex':'kaos_fx_london_breakout_v1','crypto':'kaos_crypto_breakout_v1','binary':'kaos_binary_pullback_v1','options':'kaos_options_call_spread_v1'}
NAMES={'stocks':'KAOS Stocks Pullback','forex':'KAOS Forex London Breakout','crypto':'KAOS Crypto Swing Breakout','binary':'KAOS Binary Trend Pullback','options':'KAOS Options Call Spread'}
TIMEFRAMES={'stocks':'1d','forex':'1h','crypto':'4h','binary':'1m','options':'1d'}
CONTRACTS={'stocks':'cash_equity','forex':'spot_fx','crypto':'spot_crypto','binary':'fixed_expiry','options':'equity_call_vertical'}
STOCKS=['SPY','QQQ','IWM','DIA','AAPL','MSFT','NVDA','TSLA'];CRYPTO=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT','DOGEUSDT','LTCUSDT','LINKUSDT','AVAXUSDT'];FX=['EURUSD','GBPUSD','USDJPY','AUDUSD']
RISK={'riskFractionPerTrade':.005,'aggregatePlannedRiskFraction':.01,'grossNotionalFraction':1.,'martingale':False,'requiresAccountCurrencyContractMetadata':True}

def descriptors():
    return [{'market':m,'id':i,'name':NAMES[m],'executionEnabled':False,'researchOnly':True,'productionApproved':False,'riskPolicy':RISK.copy(),'timeframe':TIMEFRAMES[m],'contractType':CONTRACTS[m],'historicalOptionsPricesAvailable':False if m=='options' else None,'evidenceStatus':'requires_historical_option_contract_data' if m=='options' else 'research_profile_no_production_approval'} for m,i in IDS.items()]


def finite(value):return isinstance(value,(float,int,np.floating,np.integer)) and not isinstance(value,(bool,np.bool_)) and math.isfinite(float(value))

def size_contracts(*,equity,risk_per_contract,notional_per_contract,step,minimum,existing_planned_risk,existing_gross_notional):
    values=[equity,risk_per_contract,notional_per_contract,step,minimum,existing_planned_risk,existing_gross_notional]
    if not all(finite(v) for v in values) or min(equity,risk_per_contract,notional_per_contract,step,minimum)<=0 or min(existing_planned_risk,existing_gross_notional)<0:raise ValueError('Explicit finite broker/account sizing metadata required')
    budget=max(0.,min(equity*.005,equity*.01-existing_planned_risk));capacity=max(0.,equity-existing_gross_notional)
    quantity=math.floor(min(budget/risk_per_contract,capacity/notional_per_contract)/step)*step
    return 0. if quantity<minimum else quantity


def stock_features(bars):return DAILY.indicators(bars)
def stock_entry(f):return bool(len(f)>=200 and np.isfinite(f.iloc[-1].sma200) and f.close.iloc[-1]>f.sma200.iloc[-1] and f.rsi2.iloc[-1]<10)
def crypto_features(bars):return SWING.swing_features(np.array([[b[k] for k in ['ts','open','high','low','close']] for b in bars],dtype=float))
def crypto_entry(f):return bool(len(f)>=250 and SWING.prior.spot_signals(f,'breakout20')[-1])


def forex_setup(frame,index=None):
    """Causal local-session box and first eligible hourly decision; caller enforces once/date."""
    i=len(frame)-1 if index is None else index
    if i<59:return None
    r=frame.iloc[i];decision=int(r.end);local=pd.Timestamp(decision,unit='ms',tz='UTC').tz_convert('Europe/London')
    if local.weekday()>4 or not 8<=local.hour<11 or local.minute!=0:return None
    prior=frame.iloc[max(0,i-32):i+1];dt=pd.to_datetime(prior.ts,unit='ms',utc=True).dt.tz_convert('Europe/London');mask=(dt.dt.date==local.date())&(dt.dt.hour<7);box=prior[mask];hours=dt[mask].dt.hour.tolist()
    if hours!=list(range(7)) or any(box.end-box.ts!=HOUR):return None
    high=float(box.high.max());low=float(box.low.min());atr=float(r.atr)
    if not np.isfinite(atr) or atr<=0:return None
    if r.close>high+.1*atr and r.close>r.ema50 and r.ema20>r.ema50:side=1;stop=low-.1*atr
    elif r.close<low-.1*atr and r.close<r.ema50 and r.ema20<r.ema50:side=-1;stop=high+.1*atr
    else:return None
    # A later candle cannot reissue the day's earlier eligible setup.
    for j in range(max(59,i-32),i):
        older=frame.iloc[j];clock=pd.Timestamp(int(older.end),unit='ms',tz='UTC').tz_convert('Europe/London')
        if clock.date()!=local.date() or not 8<=clock.hour<11:continue
        earlier_long=older.close>high+.1*older.atr and older.close>older.ema50 and older.ema20>older.ema50
        earlier_short=older.close<low-.1*older.atr and older.close<older.ema50 and older.ema20<older.ema50
        if earlier_long or earlier_short:return None
    flatten=local.normalize()+pd.Timedelta(hours=16)
    return {'side':side,'stop':stop,'atr':atr,'sessionDate':str(local.date()),'flattenAt':int(flatten.timestamp()*1000),'decision':decision}


def binary_signals(f):
    prev=f.shift(1);up=(f.ema20>f.ema50)&(f.ema50>f.ema50.shift(5));down=(f.ema20<f.ema50)&(f.ema50<f.ema50.shift(5))
    call=up&(prev.low<=prev.ema20)&(f.close>f.ema20)&(f.close>prev.high)&(f.close>f.open)&f.rsi.between(45,65)
    put=down&(prev.high>=prev.ema20)&(f.close<f.ema20)&(f.close<prev.low)&(f.close<f.open)&f.rsi.between(35,55)
    ready=(np.arange(len(f))>=59)&(f.atr>0)
    return np.where(call&ready,1,np.where(put&ready,-1,0))


def history(market,bars,now):
    f=pd.DataFrame(bars)
    required=['ts','end','open','high','low','close']
    if not all(k in f for k in required):raise ValueError('Explicit closed-candle start/end and OHLC required')
    a=f[required].to_numpy(dtype=float)
    if not len(a) or not np.isfinite(a).all() or np.any(a[:,0]>=a[:,1]) or np.any(a[:,1]>now) or np.any(np.diff(a[:,0])<=0) or np.any(a[:-1,1]>a[1:,0]):raise ValueError('Invalid, overlapping, forming or unordered history')
    if np.any(a[:,2:]<=0) or np.any(a[:,4]>np.minimum(a[:,2],a[:,5])) or np.any(a[:,3]<np.maximum(a[:,2],a[:,5])):raise ValueError('Invalid OHLC')
    if market=='stocks':
        starts=pd.to_datetime(f.ts,unit='ms',utc=True).dt.tz_convert('America/New_York');ends=pd.to_datetime(f.end,unit='ms',utc=True).dt.tz_convert('America/New_York')
        if not ((starts.dt.hour==9)&(starts.dt.minute==30)&ends.dt.hour.isin([13,16])&(ends.dt.minute==0)).all() or starts.dt.date.duplicated().any():raise ValueError('Daily regular-session bars required')
    tf={'forex':HOUR,'crypto':4*HOUR,'binary':60000}.get(market)
    if tf is not None and (np.any(a[:,1]-a[:,0]!=tf) or np.any(a[:,0]%tf)):raise ValueError('Incorrect requested-candle duration/alignment')
    if market in ['crypto','binary'] and np.any(np.diff(a[:,0])!=tf):raise ValueError('Gapped price history')
    if market=='forex':
        for i in np.flatnonzero(a[1:,0]>a[:-1,1]):
            before=pd.Timestamp(a[i,1],unit='ms',tz='UTC');after=pd.Timestamp(a[i+1,0],unit='ms',tz='UTC')
            if not (before.weekday()==4 and after.weekday() in (6,0) and after.value-before.value<=80*HOUR*1000000):raise ValueError('Unscheduled forex history gap')
    return f


def spread_candidate(chain,symbol,spot,now):
    valid=[]
    for c in chain:
        try:
            nums=[c[k] for k in ['bid','ask','strike','delta','openInterest','multiplier','observedAt','expiry']]
            if not all(finite(v) for v in nums) or c['underlying']!=symbol or c['right']!='CALL' or not isinstance(c['symbol'],str):continue
            bid,ask=c['bid'],c['ask'];dte=(c['expiry']-now)/DAY
            if not 0<bid<=ask or not 30<=dte<=60 or not 0<=now-c['observedAt']<=30000 or c['openInterest']<100 or c['multiplier']<=0 or c['strike']<=0 or (ask-bid)/((ask+bid)/2)>.2:continue
            valid.append(c)
        except (KeyError,TypeError):continue
    choices=[]
    for long in valid:
        if not .45<=long['delta']<=.60:continue
        for short in valid:
            if not .20<=short['delta']<=.35 or short['expiry']!=long['expiry'] or short['strike']<=long['strike'] or short['multiplier']!=long['multiplier'] or short['symbol']==long['symbol']:continue
            debit=long['ask']-short['bid'];width=short['strike']-long['strike'];mult=long['multiplier'];fees=4*.65;risk=debit*mult+fees;profit=(width-debit)*mult-fees
            if not 0<debit<width or risk<=0 or profit/risk<1:continue
            choices.append(((abs((long['expiry']-now)/DAY-45),abs(long['strike']-spot),abs(short['delta']-.3),long['symbol'],short['symbol']),{'longContract':long['symbol'],'shortContract':short['symbol'],'expiry':long['expiry'],'multiplier':mult,'debitPerUnderlyingUnit':debit,'riskPerSpread':risk,'maxProfitPerSpread':profit,'commissionReserve':fees,'exitPolicy':'50%maxprofit / 50%debitrisk / underlyinglosesEMA50 /21DTE','historicalOptionPnLValidated':False,'requiresAtomicSpreadOrder':True,'fillGuaranteed':False}))
    return min(choices,key=lambda x:x[0])[1] if choices else None


def manage_spread(result,chain,position,features,now):
    def hold(reason):return {**result,'reason':reason}
    required=['expiry','multiplier','entryCostPerSpread','riskPerSpread','maxProfitPerSpread']
    if not all(finite(position.get(k)) and position[k]>0 for k in required):return hold('options_spread_ledger_required_for_exit_policy')
    legs={c.get('symbol'):c for c in chain if isinstance(c,dict)}
    long=legs.get(position.get('longContract'));short=legs.get(position.get('shortContract'))
    if long is None or short is None:return hold('current_option_exit_quotes_required')
    for leg in [long,short]:
        if not all(finite(leg.get(k)) for k in ['bid','ask','observedAt','expiry','multiplier']) or not 0<=leg['bid']<=leg['ask'] or not 0<=now-leg['observedAt']<=30000 or leg['expiry']!=position['expiry'] or leg['multiplier']!=position['multiplier'] or leg.get('underlying')!=result['symbol'] or leg.get('right')!='CALL':return hold('invalid_or_stale_option_exit_quotes')
    credit=(long['bid']-short['ask'])*position['multiplier']-2*.65
    pnl=credit-position['entryCostPerSpread'];reason=None
    if (position['expiry']-now)/DAY<=21:reason='option_time_exit'
    elif features is not None and features.close.iloc[-1]<features.ema50.iloc[-1]:reason='underlying_trend_exit'
    elif pnl>=.5*position['maxProfitPerSpread']:reason='option_profit_target'
    elif pnl<=-.5*position['riskPerSpread']:reason='option_debit_loss_limit'
    if reason:return {**result,'action':'EXIT_SPREAD','reason':reason,'estimatedCreditAfterExitCommission':credit,'modeledPnLPerSpread':pnl,'quantity':None,'fillGuaranteed':False}
    return hold('defined_risk_spread_open')


def evaluate(request):
    market=request.get('market');symbol=request.get('symbol');now=request.get('nowMs');ctx=request.get('context',{});quote=request.get('quote',{})
    if market not in IDS:raise ValueError('Choose stocks,forex,crypto,binary oroptions')
    result={'profile':IDS[market],'name':NAMES[market],'market':market,'symbol':symbol,'action':'HOLD','researchOnly':True,'executionEnabled':False,'productionApproved':False,'riskPolicy':RISK.copy()}
    def hold(reason):return {**result,'reason':reason}
    if not isinstance(symbol,str) or not symbol:return hold('symbol_required')
    canonical_fx=symbol.replace('=X','')
    if market=='forex':symbol=canonical_fx;result['symbol']=symbol
    quoted_symbol=quote.get('symbol','')
    if market=='forex' and isinstance(quoted_symbol,str):quoted_symbol=quoted_symbol.replace('=X','')
    if quoted_symbol!=symbol:return hold('quote_instrument_mismatch')
    if (market in ['stocks','options'] and symbol not in STOCKS) or (market=='crypto' and symbol not in CRYPTO) or (market=='forex' and canonical_fx not in FX):return hold('unsupported_market_symbol')
    if request.get('timeframe')!=TIMEFRAMES[market] or request.get('contractType')!=CONTRACTS[market]:return hold('timeframe_or_contract_type_mismatch')
    if ctx.get('hasPendingOrder') is not False:return hold('pending_order_state_required')
    if not isinstance(now,int) or isinstance(now,bool) or now<=0:raise ValueError('Integer current timestamp required')
    if not finite(quote.get('observedAt')) or not 0<=now-quote['observedAt']<=(5000 if market=='binary' else 30000):return hold('stale_or_future_quote')
    if market=='binary':
        if not finite(quote.get('price')) or quote['price']<=0 or not finite(quote.get('payout')) or not .8<=quote['payout']<=1 or ctx.get('broker')!='pocket_option':return hold('binary_contract_quote_or_payout_unverified')
    elif not finite(quote.get('bid')) or not finite(quote.get('ask')) or not 0<quote['bid']<=quote['ask']:return hold('bid_ask_required')
    if not isinstance(ctx.get('hasOpenPosition'),bool):return hold('position_state_required')
    if not isinstance(ctx.get('consumedIntentIds'),list):return hold('consumed_intent_state_required')
    position=ctx.get('position',{})
    def emit(action,anchor,**payload):
        identity=hashlib.sha256(f'{IDS[market]}:{symbol}:{anchor}:{action}'.encode()).hexdigest()
        if identity in ctx['consumedIntentIds']:return hold('intent_already_consumed')
        return {**result,'action':action,'intentId':identity,**payload}
    if ctx['hasOpenPosition']:
        if position.get('profile')!=IDS[market] or position.get('symbol')!=symbol or not finite(position.get('entryAt')):return hold('position_profile_or_ledger_mismatch')
        if market=='binary':return emit('AWAIT_SETTLEMENT' if finite(position.get('expiresAt')) and now>=position['expiresAt'] else 'HOLD',position['entryAt'],reason='existing_fixed_expiry_contract')
        if market=='options':
            managed=manage_spread(result,request.get('optionChain',[]),position,None,now)
            if managed['action']=='EXIT_SPREAD':return emit('EXIT_SPREAD',position['entryAt'],**{k:v for k,v in managed.items() if k not in result and k!='action'})
        else:
            if not finite(position.get('stop')) or position.get('side') not in [-1,1]:return hold('position_management_metadata_required')
            price=quote['bid'] if position['side']>0 else quote['ask']
            stop_hit=price<=position['stop'] if position['side']>0 else price>=position['stop']
            due=(market=='crypto' and now-position['entryAt']>=7*DAY) or (market=='forex' and finite(position.get('flattenAt')) and now>=position['flattenAt'])
            if stop_hit or due:
                if market=='stocks' and not (finite(ctx.get('sessionOpen')) and finite(ctx.get('sessionClose')) and ctx['sessionOpen']<=now<ctx['sessionClose']):return emit('SCHEDULE_EXIT_NEXT_OPEN',position['entryAt'],reason='stop_outside_verified_regular_session',quantity=None)
                return emit('EXIT',position['entryAt'],reason='current_quote_stop' if stop_hit else 'maximum_hold_or_session_end',observedExitQuote=price,quantity=None)
            if market=='forex' and not finite(position.get('flattenAt')):return hold('forex_flatten_metadata_required')
    try:f=history('stocks' if market=='options' else market,request.get('candles',[]),now)
    except (ValueError,TypeError,KeyError):return hold('invalid_or_forming_history')
    minimum=200 if market in ['stocks','options'] else 250 if market=='crypto' else 60
    if len(f)<minimum:return hold('insufficient_history')
    decision=int(f.end.iloc[-1]);features=stock_features(f.to_dict('records')) if market in ['stocks','options'] else crypto_features(f.to_dict('records')) if market=='crypto' else TECH.indicators(f)
    position=ctx.get('position',{})
    if ctx['hasOpenPosition']:
        if market=='options':
            managed=manage_spread(result,request.get('optionChain',[]),position,features,now)
            if managed['action']=='EXIT_SPREAD':return emit('EXIT_SPREAD',position['entryAt'],**{k:v for k,v in managed.items() if k not in result and k!='action'})
            return managed
        if market=='binary':return {**result,'action':'AWAIT_SETTLEMENT' if finite(position.get('expiresAt')) and now>=position['expiresAt'] else 'HOLD','reason':'existing_fixed_expiry_contract'}
        if not finite(position.get('stop')) or position.get('side') not in [-1,1]:return hold('position_management_metadata_required')
        side=position['side'];price=quote['bid'] if side>0 else quote['ask'];reason=None
        if (side>0 and price<=position['stop']) or (side<0 and price>=position['stop']):reason='current_quote_stop'
        elif market=='stocks' and ((decision>position['entryAt'] and features.close.iloc[-1]>features.mean5.iloc[-1]) or ctx.get('heldBars',0)>=5):reason='daily_mean_or_time_exit'
        elif market=='crypto' and finite(position.get('entryAt')) and now-position['entryAt']>=7*DAY:reason='maximum_hold'
        elif market=='crypto' and decision>position.get('lastDecision',0) and (features.close.iloc[-1]<features.ema50.iloc[-1] or features.close.iloc[-1]<features.low10.iloc[-1]):reason='closed_trend_exit'
        elif market=='forex' and (not finite(position.get('flattenAt')) or now>=position['flattenAt']):reason='session_flatten_due'
        elif market=='options':return hold('options_spread_ledger_required_for_exit_policy')
        if reason:
            if market=='stocks' and not (finite(ctx.get('sessionOpen')) and ctx.get('previousSessionClose')==decision and 0<=now-ctx['sessionOpen']<=120000):return emit('SCHEDULE_EXIT_NEXT_OPEN',position['entryAt'],reason=reason,quantity=None)
            return emit('EXIT',position['entryAt'],reason=reason,observedExitQuote=price,quantity=None)
        if market=='crypto' and decision>position.get('lastDecision',0):
            stop=max(position['stop'],float(features.highclose20.iloc[-1]-3*features.atr.iloc[-1]));return emit('EXIT' if quote['bid']<=stop else 'UPDATE_STOP',position['entryAt'] if quote['bid']<=stop else f"{position['entryAt']}:{decision}",newStop=stop,effectiveAt=now,reason='closed_bar_trailing_update')
        return hold('position_open')
    if market in ['stocks','options']:
        if not all(finite(ctx.get(k)) for k in ['sessionOpen','sessionClose','previousSessionClose']) or ctx['previousSessionClose']!=decision or not ctx['previousSessionClose']<ctx['sessionOpen']<ctx['sessionClose']:return hold('exchange_calendar_context_required')
        minutes=(now-ctx['sessionOpen'])/60000
        if not (0<=minutes<=2 if market=='stocks' else 15<=minutes<=60) or now>=ctx['sessionClose']:return hold('outside_entry_session_window')
    elif not 0<=now-decision<=(10000 if market=='binary' else 120000):return hold('missed_closed_bar_entry_window')
    side=0;extra={}
    if market=='stocks':
        if not stock_entry(features):return hold('no_stock_pullback')
        side=1;extra={'stop':quote['ask']-2*float(features.atr.iloc[-1]),'exitPolicy':'nextopen afterclose>mean5or5dailybars;protectivestop'}
    elif market=='crypto':
        if not crypto_entry(features):return hold('no_crypto_breakout')
        risk=3*float(features.atr.iloc[-1])
        if not .01*quote['ask']<=risk<quote['ask']:return hold('crypto_fee_budget_or_stop_invalid')
        side=1;extra={'stop':quote['ask']-risk,'maxHoldSeconds':7*86400,'exitPolicy':'nonretroactive20close/3ATRtrail,EMA50orprior10lowexit'}
    elif market=='forex':
        if not isinstance(ctx.get('sessionAlreadyTraded'),bool):return hold('forex_session_state_required')
        if ctx['sessionAlreadyTraded']:return hold('already_traded_london_date')
        setup=forex_setup(features)
        if setup is None:return hold('no_complete_london_box_breakout')
        side=setup['side'];entry=quote['ask'] if side>0 else quote['bid'];risk=side*(entry-setup['stop'])
        if risk<=0 or 2*risk/entry<.001:return hold('forex_cost_budget_or_stop_invalid')
        extra={'stop':setup['stop'],'target':entry+side*2*risk,'flattenAt':setup['flattenAt'],'sessionDate':setup['sessionDate']}
    elif market=='binary':
        side=int(binary_signals(features)[-1])
        if not side:return hold('no_binary_trend_pullback')
        extra={'expirySeconds':300,'expiresAt':now+300000,'payout':quote['payout'],'noMartingale':True}
    else:
        if not stock_entry(features) or features.ema50.iloc[-1]<=features.ema200.iloc[-1]:return hold('no_bullish_underlying_pullback')
        if not request.get('optionChain'):return hold('historical_and_current_option_contract_data_required')
        spread=spread_candidate(request['optionChain'],symbol,quote['ask'],now)
        if spread is None:return hold('no_fresh_liquid_defined_risk_call_spread')
        side=1;extra=spread
    if 'stop' in extra and extra['stop']<=0:return hold('invalid_positive_price_stop')
    action=('CALL' if side>0 else 'PUT') if market=='binary' else 'BULL_CALL_SPREAD' if market=='options' else 'BUY' if side>0 else 'SELL'
    return emit(action,decision,decision=decision,quoteObservedAt=quote['observedAt'],entryReference=quote['price'] if market=='binary' else quote['ask'] if side>0 else quote['bid'],quantity=None,requiresBrokerAccountSizing=True,**extra)
