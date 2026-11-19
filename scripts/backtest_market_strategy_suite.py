"""One fixed profile per market; no parameter selection or real orders."""
import argparse,hashlib,importlib.util,json,csv
from pathlib import Path
import numpy as np,pandas as pd
import backtest_video_strategies as base
import research_daily_edge as daily
import research_kaos_swing as swing
from backtest_all_timeframes import aggregate
from pulse_v2_replay import parts,binary
from research_kaos_candidates import summarize as binary_stats
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_market_suite_v1'
spec=importlib.util.spec_from_file_location('suite_eval',OUT/'strategies.py');suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)

def dump(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def checked(directory,kind=None):
    m=json.loads((directory/'manifest.json').read_text());records=[]
    for symbol,info in m['assets'].items():
        if kind and info.get('kind')!=kind:continue
        raw=(directory/info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Snapshot checksum mismatch')
        records.append(json.loads(raw))
    return records,m


def fx_replay(asset,f,stress=False):
    ts=f.ts.to_numpy();op=f.open.to_numpy();hi=f.high.to_numpy();lo=f.low.to_numpy();out=[];used=set();slip=.0002 if stress else .0001
    for i in range(59,len(f)):
        setup=suite.forex_setup(f,i)
        if not setup or setup['sessionDate'] in used:continue
        used.add(setup['sessionDate']);entry_i=int(np.searchsorted(ts,setup['decision']))+int(stress);exit_i=int(np.searchsorted(ts,setup['flattenAt']))
        if entry_i>=len(f) or exit_i>=len(f) or entry_i>=exit_i or ts[exit_i]!=setup['flattenAt'] or np.any(np.diff(ts[entry_i:exit_i+1])!=suite.HOUR):continue
        side=setup['side'];entry=float(op[entry_i]);risk=side*(entry-setup['stop'])
        if risk<=0 or 2*risk/entry<.001:continue
        stop=setup['stop'];target=entry+side*2*risk;price=float(op[exit_i]);jexit=exit_i;reason='london_close'
        for j in range(entry_i,exit_i):
            if (side>0 and op[j]<=stop) or (side<0 and op[j]>=stop):price=float(op[j]);jexit=j;reason='gap_stop';break
            if (side>0 and op[j]>=target) or (side<0 and op[j]<=target):price=target;jexit=j;reason='target';break
            stop_hit=lo[j]<=stop if side>0 else hi[j]>=stop;target_hit=hi[j]>=target if side>0 else lo[j]<=target
            if stop_hit:price=stop;jexit=j;reason='stop';break
            if target_hit:price=target;jexit=j;reason='target';break
        paid=entry*(1+side*slip);received=price*(1-side*slip);net=side*(received-paid)
        out.append({'asset':asset,'entry':int(ts[entry_i]),'exit':int(ts[jexit]),'side':side,'entryPrice':paid,'exitPrice':received,'netR':net/risk,'netBps':net/entry*10000,'reason':reason,'executionEnabled':False})
    return out


def metric(rows):
    m=swing.metrics(rows,15);m['meanNetBps']=float(np.mean([r['netBps'] for r in rows])) if rows else None;return m


def main():
    p=argparse.ArgumentParser();p.add_argument('--daily',type=Path,required=True);p.add_argument('--recent-daily',type=Path,required=True);p.add_argument('--hourly',type=Path,required=True);p.add_argument('--fx',type=Path,required=True);p.add_argument('--po',type=Path,required=True);a=p.parse_args();historical,hm=checked(a.daily,'stocks');recent,rm=checked(a.recent_daily,'stocks');fxrecords,fm=checked(a.fx,'forex');stocks={};stock_rows=[]
    oldplan=json.loads((ROOT/'research/daily_edge_v1/plan.json').read_text())
    for label,records,start,end in [('etf_2018_2020',historical,'2018-01-01','2021-01-01'),('etf_2021_2024',historical,'2021-01-01','2025-01-01'),('eight_stocks_2026',recent,'2026-01-01','2026-11-01')]:
        frames={r['symbol']:suite.stock_features(r['bars']) for r in records};bounds=(base.stamp(start),base.stamp(end));b,rows=daily.group(records,frames,'stocks','rsi2_bull_pullback',*bounds,oldplan);stress,_=daily.group(records,frames,'stocks','rsi2_bull_pullback',*bounds,oldplan,2);benchmark,_=daily.group(records,frames,'stocks','rsi2_bull_pullback',*bounds,oldplan,benchmark=True)
        stocks[label]={'base':b,'double_costs':stress,'buy_hold':benchmark,'productionApproved':False};stock_rows.extend({'period':label,**r} for r in rows);print('STOCKS',label,'return%',b['return_pct'],'trades',b['trades'],flush=True)
    dump('stocks_results.json',stocks)
    with (OUT/'stocks_trades.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(stock_rows[0]) if stock_rows else ['symbol'],lineterminator='\n');w.writeheader();w.writerows(stock_rows)
    all_fx=[];all_fx_stress=[]
    for record in fxrecords:
        for segment in parts(record['bars'],'forex'):
            if len(segment)<60:continue
            frame=suite.TECH.indicators(pd.DataFrame(segment));all_fx+=fx_replay(record['symbol'],frame);all_fx_stress+=fx_replay(record['symbol'],frame,True)
    forex={}
    for label,start,end in [('2025','2025-01-01','2026-01-01'),('2026','2026-01-01','2026-11-01')]:
        bounds=(base.stamp(start),base.stamp(end));rows=[r for r in all_fx if bounds[0]<=r['entry'] and r['exit']<bounds[1]];stress=[r for r in all_fx_stress if bounds[0]<=r['entry'] and r['exit']<bounds[1]];forex[label]={'base':metric(rows),'stress':metric(stress),'productionApproved':False};print('FX',label,forex[label]['base'],flush=True)
    dump('forex_results.json',forex)
    with (OUT/'forex_trades.csv').open('w') as f:
        rows=[{'scenario':'base',**r} for r in all_fx]+[{'scenario':'stress',**r} for r in all_fx_stress];w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['asset'],lineterminator='\n');w.writeheader();w.writerows(rows)
    cm=json.loads((a.hourly/'manifest.json').read_text());prepared={14400:[]}
    for asset,info in cm['assets'].items():
        path=a.hourly/info['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Hourly checksum mismatch')
        data=np.load(path,allow_pickle=False)
        for seg in np.split(data,np.where(np.diff(data[:,0])!=suite.HOUR)[0]+1):
            if not len(seg):continue
            bars=aggregate(seg,14400,3600)
            if len(bars)>=250:prepared[14400].append((asset,seg,suite.SWING.swing_features(bars)))
    rows,crypto=swing.swing_eval(prepared,(14400,'breakout20',3),(base.stamp('2021-01-01'),base.stamp('2025-01-01')));crypto['base']=swing.metrics(rows,15);crypto['productionApproved']=False;dump('crypto_results.json',crypto);print('CRYPTO',crypto['base'],flush=True)
    po_parts,pm=base.load_po(a.po);bounds=(base.stamp('2026-09-27'),base.stamp('2026-10-05 18:10:50'));po=[];po_stress=[]
    for asset,data in po_parts:
        data=data[data[:,0]<bounds[1]]
        if not len(data):continue
        bars=aggregate(data,60,5)
        if len(bars)<60:continue
        frame=pd.DataFrame(bars,columns=['ts','open','high','low','close']);frame['end']=frame.ts+60000;features=suite.TECH.indicators(frame);signal=suite.binary_signals(features);po+=binary(asset,data,frame,signal,5,bounds);po_stress+=binary(asset,data,frame,signal,5,bounds,True)
    binary_report={'base':binary_stats(po,True,15),'stress':binary_stats(po_stress,True,15),'source':pm,'reserved_evaluated':False,'productionApproved':False,'operationalMinimumPayout':.8};dump('binary_results.json',binary_report);print('BINARY',binary_report['base'],flush=True)
    dump('catalog.json',suite.descriptors());dump('options_status.json',{'profile':suite.IDS['options'],'status':'quote-gated_implementation_no_historical_option_PnL','reason':'Historical option contracts/Greeks/assignment/fill data unavailable','productionApproved':False})
    hashfiles=[OUT/'plan.json',OUT/'daily_snapshot_plan.json',OUT/'strategies.py',ROOT/'scripts/evaluate_market_strategy.py',Path(__file__),ROOT/'research/daily_edge_v1/strategy.py',ROOT/'research/kaos_swing_v1/strategy.py',ROOT/'research/kaos_pulse_v2/strategy.py']
    dump('provenance.json',{'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in hashfiles},'source_manifests':{'historical_daily':hm,'recent_daily':rm,'crypto_hourly':cm,'indicative_fx':fm},'reserved_new_three_crypto_2025_evaluated':False,'reserved_PO_evaluated':False,'executionEnabled':False,'trainedAI':False,'profilesCompared':5,'parameterSearch':False});print('COMPLETE',flush=True)
if __name__=='__main__':main()
