"""Frozen PULSE revision across crypto, stocks, indicative FX and separate binaries."""
import argparse,csv,hashlib,importlib.util,itertools,json
from pathlib import Path
import numpy as np
import pandas as pd
import backtest_video_strategies as old
from backtest_all_timeframes import aggregate
from review_uploaded_kaos_v1 import pure_modules
import research_kaos_swing as swing
from research_kaos_candidates import summarize as binary_stats
import pulse_v2_replay as replay
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_pulse_v2'
spec=importlib.util.spec_from_file_location('pulse_v2',OUT/'strategy.py');v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)

def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def metrics(rows,adjust=1):
    m=swing.metrics(rows,adjust);m['meanNetBps']=float(np.mean([r['netBps'] for r in rows])) if rows else None
    weeks={}
    for row in rows:
        week=(row['entry']+3*86400000)//(7*86400000);weeks[week]=weeks.get(week,0)+row['netR']
    vals=np.array(list(weeks.values()));m['lower_week_mean']=None
    if len(vals)>1:
        rng=np.random.default_rng(219);means=rng.choice(vals,(5000,len(vals)),replace=True).mean(1)
        m['lower_week_mean']=float(np.quantile(means,.05/adjust if adjust>1 else .025))
    return m

def price_gate(r,baselines,final=False):
    b=r['base'];return bool(b['trades']>=(60 if final else 150) and b['days']>=(40 if final else 90) and b['PF'] is not None and b['PF']>=(1.1 if final else 1.15) and sum(v>0 for v in b['asset_netR'].values())>=(2 if final else 4) and b['lower_week_mean'] is not None and b['lower_week_mean']>0 and r['stress']['netR']>0 and all(x['base']['meanNetBps'] is not None and b['meanNetBps']>x['base']['meanNetBps'] for x in baselines.values()))

def prepare(records,kind,legacy):
    ready={tf:[] for tf in [3600,14400]}
    for asset,record in records.items():
        for base in replay.parts(record['bars'],kind):
            for tf in ready:
                frame=replay.requested(base,tf,kind)
                if len(frame)<60:continue
                original=legacy.indicators(frame,legacy.DEFAULT);sig=legacy.signal_series(original,legacy.DEFAULT);sig[:60]=0
                if kind!='forex':sig=np.where(sig>0,1,0)
                ready[tf].append({'asset':asset,'base':base,'frame':frame,'v2':v2.indicators(frame),'legacySig':sig,'legacyATR':original.atr.to_numpy(),'dividends':record.get('dividends',[])})
    return ready


def evaluate(prepared,kind,tf,guard,target,bounds,baseline=None,assets=None,final=False):
    rows=[];stress=[]
    for item in prepared[tf]:
        if assets is not None and item['asset'] not in assets:continue
        if baseline is not None:sig=item['legacySig'];atr=item['legacyATR'];multiple=5;tp=3;budget=v2.cost_budget if baseline=='cost_filtered_original' else None
        else:sig=v2.signals(item['v2'],guard,kind=='forex');atr=item['v2'].atr.to_numpy();multiple=2;tp=target;budget=v2.cost_budget
        for dst,stressed in [(rows,False),(stress,True)]:dst.extend(replay.brackets(item['asset'],item['base'],item['frame'],sig,atr,tp,multiple,bounds,kind,budget,stressed,item['dividends']))
    return rows,{'base':metrics(rows,1 if final else 24),'stress':metrics(stress)}


def checked_json(directory,meta):
    path=directory/meta['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Snapshot checksum mismatch')
    return json.loads(path.read_text())


def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--crypto',type=Path,required=True);p.add_argument('--markets',type=Path,required=True);p.add_argument('--equities',type=Path,required=True);p.add_argument('--po',type=Path,required=True);a=p.parse_args();legacy,_=pure_modules(a.package);plan=json.loads((OUT/'plan.json').read_text());amend=json.loads((OUT/'scope_amendment.json').read_text())
    cm=json.loads((a.crypto/'manifest.json').read_text());mm=json.loads((a.markets/'manifest.json').read_text());em=json.loads((a.equities/'manifest.json').read_text());crypto={};stocks={};forex={}
    for asset,m in cm['assets'].items():
        path=a.crypto/m['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Crypto checksum mismatch')
        data=np.load(path,allow_pickle=False)
        if len(data)!=m['bars'] or np.any(np.diff(data[:,0])<=0):raise ValueError('Bad hourly sequence')
        crypto[asset]={'bars':[{'ts':int(ts),'end':int(ts)+3600000,'open':o,'high':h,'low':l,'close':c,'session_start':None,'session_end':None} for ts,o,h,l,c in data]}
    for asset,m in mm['assets'].items():
        if m['kind'] not in ('stocks','forex'):continue
        record=checked_json(a.markets,m);(stocks if m['kind']=='stocks' else forex)[asset]=record
    for asset,m in em['assets'].items():
        if 'file' in m:stocks[asset]=checked_json(a.equities,m)
    dump('provenance.json',{'plan_sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),'amendment_sha256':hashlib.sha256((OUT/'scope_amendment.json').read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256((OUT/'strategy.py').read_bytes()).hexdigest(),'replay_sha256':hashlib.sha256((ROOT/'scripts/pulse_v2_replay.py').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'crypto_sources':cm,'existing_market_sources':mm,'new_stock_sources':em,'executionEnabled':False})
    grid=list(itertools.product([3600,14400],[False,True],[3,4]));results={};baselines={};coverage={};prepared_crypto=None
    for kind,records in [('crypto',crypto),('stocks',stocks),('forex',forex)]:
        prepared=prepare(records,kind,legacy)
        if kind=='crypto':prepared_crypto=prepared
        coverage[kind]={str(tf):{asset:{'segments':sum(item['asset']==asset for item in items),'requested_history_bars':sum(len(item['frame']) for item in items if item['asset']==asset),'ready_60':sum(max(0,len(item['frame'])-59) for item in items if item['asset']==asset),'ready_250':sum(max(0,len(item['frame'])-249) for item in items if item['asset']==asset)} for asset in records} for tf,items in prepared.items()}
        dump('coverage.json',coverage)
        bounds=tuple(old.stamp(x) for x in (plan['validation'] if kind=='crypto' else amend[kind]['evaluation']));baselines[kind]={};results[kind]={}
        for tf in [3600,14400]:
            baselines[kind][str(tf)]={}
            for name in ['corrected_original','cost_filtered_original']:
                _,r=evaluate(prepared,kind,tf,False,3,bounds,baseline=name);baselines[kind][str(tf)][name]=r
        for tf,guard,target in grid:
            key=f'{tf}:trend{int(guard)}:target{target}';rows,r=evaluate(prepared,kind,tf,guard,target,bounds);r['gate']=price_gate(r,baselines[kind][str(tf)]);results[kind][key]=r
            print(kind,key,'trades',r['base']['trades'],'netR',round(r['base']['netR'],2),'PF',r['base']['PF'],'gate',r['gate'],flush=True)
        dump('price_results.json',results);dump('baselines.json',baselines)
    eligible=[key for key,r in results['crypto'].items() if r['gate']];selected=sorted(eligible,key=lambda k:(-results['crypto'][k]['base']['lower_week_mean'],k))[0] if eligible else None;dump('selection.json',{'selected':selected,'frozen_before_confirmation':True,'confirmation_evaluated':selected is not None,'executionEnabled':False});confirmation={'qualified':False,'state':'not_opened','executionEnabled':False}
    if selected:
        tf,g,t=selected.split(':');tf=int(tf);guard=bool(int(g[-1]));target=int(t[-1]);assets=set(plan['confirmation_assets']);bounds=tuple(old.stamp(x) for x in plan['confirmation']);b={}
        for name in ['corrected_original','cost_filtered_original']:_,b[name]=evaluate(prepared_crypto,'crypto',tf,False,3,bounds,baseline=name,assets=assets,final=True)
        rows,r=evaluate(prepared_crypto,'crypto',tf,guard,target,bounds,assets=assets,final=True);confirmation={'selected':selected,**r,'baselines':b,'qualified':price_gate(r,b,True),'executionEnabled':False}
        with (OUT/'confirmation_trades.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['asset'],lineterminator='\n');w.writeheader();w.writerows(rows)
    dump('confirmation.json',confirmation)
    poparts,pometa=old.load_po(a.po);bounds=(old.stamp('2026-09-27'),old.stamp('2026-10-05 18:10:50'));po_prepared={tf:[] for tf in [30,60]}
    for asset,data in poparts:
        data=data[data[:,0]<bounds[1]]
        if not len(data):continue
        for tf in po_prepared:
            bars=aggregate(data,tf,5)
            if len(bars)<60:continue
            f=pd.DataFrame(bars,columns=['ts','open','high','low','close']);f['end']=f.ts+tf*1000;original=legacy.indicators(f,legacy.DEFAULT);sig=legacy.signal_series(original,legacy.DEFAULT);sig[:60]=0
            po_prepared[tf].append((asset,data,f,v2.indicators(f),sig))
    binary={};binary_baselines={}
    for tf,guard,expiry in itertools.product([30,60],[False,True],[1,3]):
        key=f'{tf}:trend{int(guard)}:expiry{expiry}';rows=[];stress=[];original_rows=[];original_stress=[]
        for asset,data,f,features,original in po_prepared[tf]:
            sig=v2.signals(features,guard,True);rows+=replay.binary(asset,data,f,sig,expiry,bounds);stress+=replay.binary(asset,data,f,sig,expiry,bounds,True)
            original_rows+=replay.binary(asset,data,f,original,expiry,bounds);original_stress+=replay.binary(asset,data,f,original,expiry,bounds,True)
        b=binary_stats(rows,True,8);s=binary_stats(stress,True);gate=bool(b['wins']+b['losses']>=200 and b['days']>=3 and b['wilson_lower']>1/1.8 and b['lower_day_bootstrap_mean'] is not None and b['lower_day_bootstrap_mean']>0 and s['net']>0 and sum(v>0 for v in b['asset_net'].values())>=2)
        binary[key]={'base':b,'stress':s,'descriptive_gate':gate};binary_baselines[f'{tf}:{expiry}']={'base':binary_stats(original_rows,True,8),'stress':binary_stats(original_stress,True)};print('binary',key,'trades',b['trades'],'WR',b['win_rate'],'gate',gate,flush=True)
    dump('binary_results.json',{'source':pometa,'reserved_evaluated':False,'results':binary,'baselines':binary_baselines,'executionEnabled':False});dump('paper_release.json',{'strategy':'KAOS PULSE v2','selected':selected,'historical_gate_passed':confirmation['qualified'],'researchOnly':True,'executionEnabled':False,'note':'Price-based and fixed-expiry results are separate; no native platform or production integration.'});print('COMPLETE selected',selected,'confirmation',confirmation['qualified'],flush=True)
if __name__=='__main__':main()
