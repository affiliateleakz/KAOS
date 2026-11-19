"""Timestamped public-quote paper observations. No authenticated/order API exists."""
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,math,os,sqlite3,time
from pathlib import Path
import httpx
import numpy as np
from backtest_all_timeframes import aggregate
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('paper_rules',ROOT/'research/kaos_swing_v1/strategy.py');rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
HOUR=3600000;TF=4*HOUR
COINBASE={symbol+'USDT':symbol+'-USD' for symbol in ['BTC','ETH','SOL','XRP','ADA','DOGE','LTC','LINK','AVAX']}
ASSETS=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT','DOGEUSDT','LTCUSDT','LINKUSDT','AVAXUSDT']

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def fingerprint():return hashlib.sha256(b''.join(p.read_bytes() for p in [Path(__file__),ROOT/'research/kaos_swing_v1/strategy.py',ROOT/'research/kaos_candidate_v1/strategy.py',ROOT/'scripts/backtest_all_timeframes.py'])).hexdigest()

def database(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);conn=sqlite3.connect(path,timeout=15);os.chmod(path,0o600)
    conn.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,symbol TEXT,ts INTEGER,payload TEXT);
    CREATE TABLE IF NOT EXISTS bars(symbol TEXT,ts INTEGER,payload TEXT,PRIMARY KEY(symbol,ts));
    CREATE TABLE IF NOT EXISTS positions(symbol TEXT PRIMARY KEY,payload TEXT);
    CREATE TABLE IF NOT EXISTS state(symbol TEXT PRIMARY KEY,payload TEXT);
    CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,ts INTEGER,symbol TEXT,kind TEXT,payload TEXT);''');return conn

def validate(obs,now,replay):
    symbol=obs.get('symbol');ts=obs.get('observedAt');bid=obs.get('bid');ask=obs.get('ask')
    if symbol not in ASSETS:raise ValueError('Unsupported research symbol')
    if isinstance(ts,bool) or not isinstance(ts,int) or ts<=0:raise ValueError('Integer observation timestamp required')
    if not replay and not -5000<=now-ts<=30000:raise ValueError('Stale or future quote; archive observations require a replay journal')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in [bid,ask]) or bid>ask:raise ValueError('Invalid bid/ask')
    a=np.asarray(obs.get('bars',[]),dtype=float)
    if a.ndim!=2 or a.shape[1]!=5 or not len(a) or not np.isfinite(a).all():raise ValueError('Finite hourly OHLC required')
    if np.any(a[:,0]%HOUR) or np.any(np.diff(a[:,0])<=0) or np.any(a[:,0]+HOUR>ts):raise ValueError('Unaligned, unordered or forming hourly candle')
    if np.any(a[:,1:]<=0) or np.any(a[:,3]>np.minimum(a[:,1],a[:,4])) or np.any(a[:,2]<np.maximum(a[:,1],a[:,4])):raise ValueError('Invalid OHLC')
    if ts-(a[-1,0]+HOUR)>HOUR+120000:raise ValueError('Stale candle feed')
    return a

def process(conn,obs,now=None,replay=False,fee_bps=10.,slippage_bps=2.):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=100 for v in [fee_bps,slippage_bps]):raise ValueError('Fee/slippage must be finite basis points between0and100')
    fee=fee_bps/10000;slip=slippage_bps/10000
    now=int(time.time()*1000) if now is None else now;a=validate(obs,now,replay);symbol=obs['symbol'];ts=obs['observedAt'];mode='replay' if replay else 'forward_public_quote';oid=hashlib.sha256(canonical(obs).encode()).hexdigest();emitted=[]
    def event(kind,payload):
        body={'mode':mode,'executionEnabled':False,'brokerOrderSubmitted':False,'researchOnly':True,'historicalQualificationPassed':False,'eligibleForPerformanceClaims':False,**payload};eid=hashlib.sha256((oid+':'+kind).encode()).hexdigest();conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(eid,ts,symbol,kind,canonical(body)));emitted.append({'kind':kind,**body})
    try:
        conn.execute('BEGIN IMMEDIATE')
        identity=canonical({'mode':mode,'engine_sha256':fingerprint(),'config':'4h:breakout20:3ATR:7d:1pct_min_risk','feed':obs.get('feed',obs.get('source','unverified_input')),'fee_bps_per_side':fee_bps,'slippage_bps_per_side':slippage_bps})
        old=conn.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
        if old and old[0]!=identity:raise ValueError('Engine/config or replay/forward mode mismatch; use a separate journal')
        conn.execute("INSERT OR IGNORE INTO meta VALUES('identity',?)",(identity,))
        if conn.execute('SELECT 1 FROM observations WHERE id=?',(oid,)).fetchone():conn.rollback();return {'duplicate':True,'events':[],'executionEnabled':False}
        found=conn.execute('SELECT payload FROM state WHERE symbol=?',(symbol,)).fetchone();state=json.loads(found[0]) if found else {'last_observed':0,'last_decision':0}
        if ts<=state['last_observed']:raise ValueError('Out-of-order observation')
        for row in a:
            bar_ts=int(row[0]);payload=canonical(row.tolist());old=conn.execute('SELECT payload FROM bars WHERE symbol=? AND ts=?',(symbol,bar_ts)).fetchone()
            if old and old[0]!=payload:raise ValueError('Conflicting immutable candle')
            conn.execute('INSERT OR IGNORE INTO bars VALUES(?,?,?)',(symbol,bar_ts,payload))
        history=np.array([json.loads(r[0]) for r in conn.execute('SELECT payload FROM bars WHERE symbol=? ORDER BY ts',(symbol,))]);gaps=np.flatnonzero(np.diff(history[:,0])!=HOUR);history=history[gaps[-1]+1:] if len(gaps) else history
        candles=aggregate(history,TF//1000,HOUR//1000);f=rules.swing_features(candles) if len(candles)>=250 else None
        decision=int(candles[-1,0])+TF if len(candles) else 0
        position_row=conn.execute('SELECT payload FROM positions WHERE symbol=?',(symbol,)).fetchone();position=json.loads(position_row[0]) if position_row else None
        if state['last_observed'] and ts-state['last_observed']>120000:
            event('COVERAGE_GAP',{'gapMs':ts-state['last_observed'],'note':'No historical stop fill is inferred during missed coverage.'})
            if position:position['coverageIncomplete']=True
        if not state['last_observed']:event('BOOTSTRAP',{'retainedHourlyBars':len(history),'firstHour':int(history[0,0]),'note':'Finite bootstrap seed differs from full historical archive; retained seed history is not rolled away.'})
        exited=False
        if position:
            reason=None
            if obs['bid']<=position['stop']:reason='observed_stop_quote'
            elif ts>=position['deadline']:reason='observed_time_exit'
            # Only fully observed intervals after this stop became active count.
            touched=history[(history[:,0]>=max(position['entryAt'],position['stopUpdatedAt']))&(history[:,0]+HOUR>state['last_observed'])]
            if reason is None and len(touched) and np.any(touched[:,3]<=position['stop']):reason='late_observed_stop_touch';event('MISSED_STOP_COVERAGE',{'stop':position['stop'],'fillPolicy':'Current observed bid only; no invented earlier fill.'})
            if reason is None and f is not None and decision>position['lastTrailDecision']:
                last=f.iloc[-1]
                if last.close<last.ema50 or last.close<last.low10:reason='closed_bar_exit_detected'
                else:
                    old_stop=position['stop'];position['stop']=max(old_stop,float(last.highclose20-3*last.atr));position['lastTrailDecision']=decision
                    if position['stop']>old_stop:
                        position['stopUpdatedAt']=ts;event('PAPER_TRAIL',{'oldStop':old_stop,'newStop':position['stop'],'decision':decision,'effectiveAt':ts})
                    if obs['bid']<=position['stop']:reason='new_trailing_stop_crossed'
            if reason:
                price=obs['bid']*(1-slip);paid=position['entryFill'];net=(price-paid-fee*(price+paid))/position['risk']
                event('PAPER_EXIT',{'reason':reason,'entryAt':position['entryAt'],'exitFill':price,'netR':net,'riskUnitsAreNotPortfolioReturns':True,'executionCoverageIncomplete':position.get('coverageIncomplete',False) or reason=='late_observed_stop_touch'});conn.execute('DELETE FROM positions WHERE symbol=?',(symbol,));position=None;exited=True
            else:conn.execute('UPDATE positions SET payload=? WHERE symbol=?',(canonical(position),symbol))
        if not position and not exited and decision>state['last_decision']:
            if f is None:event('HOLD',{'reason':'insufficient_contiguous_history'})
            elif not 0<=ts-decision<=120000:event('HOLD',{'reason':'missed_entry_window','decision':decision})
            elif not rules.prior.spot_signals(f,'breakout20')[-1]:event('HOLD',{'reason':'no_breakout','decision':decision})
            else:
                risk=3*float(f.atr.iloc[-1]);raw=obs['ask']
                if not .01*raw<=risk<raw:event('HOLD',{'reason':'fee_budget_filter'})
                else:
                    position={'entryAt':ts,'entryFill':raw*(1+slip),'risk':risk,'stop':raw-risk,'stopUpdatedAt':ts,'lastTrailDecision':decision,'deadline':ts+7*86400000,'coverageIncomplete':False}
                    conn.execute('INSERT INTO positions VALUES(?,?)',(symbol,canonical(position)));event('PAPER_ENTRY',{'decision':decision,**position,'simulatedQuoteSide':'ask','source':obs.get('source','unverified_input')})
        state.update(last_observed=ts,last_decision=max(state['last_decision'],decision));conn.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(symbol,canonical(state)));conn.execute('INSERT INTO observations VALUES(?,?,?,?)',(oid,symbol,ts,canonical(obs)));conn.commit()
    except BaseException:conn.rollback();raise
    return {'events':emitted,'mode':mode,'executionEnabled':False,'openPosition':position is not None}

def public_snapshot(symbol,bootstrap=True):
    if symbol not in ASSETS:raise ValueError('Unsupported symbol')
    now=int(time.time()*1000);end=now//HOUR*HOUR-1;rows=[]
    with httpx.Client(base_url='https://api.binance.com',timeout=15) as client:
        for _ in range(4 if bootstrap else 1):
            response=client.get('/api/v3/klines',params={'symbol':symbol,'interval':'1h','limit':1000,'endTime':end});response.raise_for_status();batch=response.json()
            if not batch:raise ValueError('Empty public candle response')
            rows=[r[:5] for r in batch if int(r[8])>0]+rows;end=int(batch[0][0])-1
        response=client.get('/api/v3/ticker/bookTicker',params={'symbol':symbol});response.raise_for_status();quote=response.json();observed=int(time.time()*1000)
    return {'symbol':symbol,'observedAt':observed,'bid':float(quote['bidPrice']),'ask':float(quote['askPrice']),'bars':[[int(r[0]),*map(float,r[1:])] for r in rows],'feed':'binance_public','product':symbol,'source':'Binance public klines/bookTicker; observed locally, no accepted broker order'}

def coinbase_snapshot(symbol,bootstrap=True):
    if symbol not in COINBASE:raise ValueError('No supported Coinbase public product for this symbol')
    product=COINBASE[symbol];end=int(time.time()*1000)//HOUR*HOUR;rows={}
    with httpx.Client(base_url='https://api.exchange.coinbase.com',timeout=15) as client:
        for _ in range(14 if bootstrap else 1):
            start=end-300*HOUR
            iso=lambda ts:datetime.fromtimestamp(ts/1000,timezone.utc).isoformat()
            response=client.get('/products/'+product+'/candles',params={'granularity':3600,'start':iso(start),'end':iso(end)});response.raise_for_status();batch=response.json()
            if not isinstance(batch,list):raise ValueError('Unexpected public candle response')
            for r in batch:
                ts=int(r[0])*1000
                if start<=ts<end and float(r[5])>0:
                    row=[ts,float(r[3]),float(r[2]),float(r[1]),float(r[4])]
                    if ts in rows and rows[ts]!=row:raise ValueError('Conflicting public candle response')
                    rows[ts]=row
            end=start
        response=client.get('/products/'+product+'/ticker');response.raise_for_status();quote=response.json();observed=int(time.time()*1000)
    return {'symbol':symbol,'product':product,'feed':'coinbase_public','observedAt':observed,'bid':float(quote['bid']),'ask':float(quote['ask']),'bars':[rows[ts] for ts in sorted(rows)],'source':'Coinbase Exchange public USD candles/ticker; local observation, no accepted broker order'}

def status(conn):
    meta=conn.execute("SELECT value FROM meta WHERE key='identity'").fetchone();closed=[json.loads(r[0]) for r in conn.execute("SELECT payload FROM events WHERE kind='PAPER_EXIT'")]
    return {'identity':json.loads(meta[0]) if meta else None,'observations':conn.execute('SELECT count(*) FROM observations').fetchone()[0],'closedPaperTrades':len(closed),'sumClosedRiskUnits':sum(r['netR'] for r in closed),'notPortfolioReturn':True,'closedTradesWithCoverageIssues':sum(bool(r['executionCoverageIncomplete']) for r in closed),'eligibleForPerformanceClaims':False,'coverageGaps':conn.execute("SELECT count(*) FROM events WHERE kind='COVERAGE_GAP'").fetchone()[0],'openPaperPositions':[json.loads(r[0]) for r in conn.execute('SELECT payload FROM positions')],'executionEnabled':False}

def main():
    os.umask(0o077);p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--symbol',choices=ASSETS,default='BTCUSDT');p.add_argument('--observation',type=Path);p.add_argument('--replay',action='store_true');p.add_argument('--status',action='store_true');p.add_argument('--provider',choices=['coinbase','binance'],default='coinbase');p.add_argument('--fee-bps',type=float);p.add_argument('--slippage-bps',type=float,default=2.);args=p.parse_args()
    if args.replay and args.observation is None:p.error('--replay requires an observation file; public snapshots are forward-only')
    conn=database(args.database)
    try:
        if args.status:
            print(canonical(status(conn)));return
        if args.observation:
            if args.observation.stat().st_size>10_000_000:raise ValueError('Observation file too large')
            obs=json.loads(args.observation.read_text())
        else:
            fetch=coinbase_snapshot if args.provider=='coinbase' else public_snapshot
            obs=fetch(args.symbol,not conn.execute('SELECT 1 FROM state WHERE symbol=?',(args.symbol,)).fetchone())
        fee=args.fee_bps if args.fee_bps is not None else (60. if args.provider=='coinbase' else 10.)
        print(canonical(process(conn,obs,replay=args.replay,fee_bps=fee,slippage_bps=args.slippage_bps)))
    except (httpx.HTTPError,ValueError,sqlite3.Error) as exc:
        message={'error':str(exc),'executionEnabled':False,'observationNotCommitted':True}
        if isinstance(exc,httpx.HTTPStatusError):message['httpStatus']=exc.response.status_code
        raise SystemExit(canonical(message))
    finally:conn.close()
if __name__=='__main__':main()
