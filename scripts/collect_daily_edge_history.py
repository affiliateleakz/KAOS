"""Capture frozen public daily OHLC/dividend snapshots for bounded strategy research."""
import argparse,hashlib,json,time,math
from pathlib import Path
from datetime import datetime,timezone
import httpx

ROOT=Path(__file__).resolve().parents[1]


def stamp(day):return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--plan',type=Path,default=ROOT/'research/daily_edge_v1/plan.json');args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True);args.cache.mkdir(parents=True,exist_ok=True)
    plan_path=args.plan;plan=json.loads(plan_path.read_text());start,end=stamp(plan['data_start']),stamp(plan['end_exclusive']);manifest={'retrievedAt':datetime.now(timezone.utc).isoformat(),'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'assets':{},'live_approved':False}
    with httpx.Client(timeout=40,follow_redirects=True,headers={'User-Agent':'KAOS-bounded-research/1.0'}) as client:
        for kind,symbols in plan['universe'].items():
            for symbol in symbols:
                url='https://query1.finance.yahoo.com/v8/finance/chart/'+symbol;params={'period1':start,'period2':end,'interval':'1d','events':'div,splits','includePrePost':'false'};cache=args.cache/(symbol.replace('=','_')+'-'+str(start)+'-'+str(end)+'.json')
                if cache.exists():raw=cache.read_bytes()
                else:
                    for attempt in range(4):
                        r=client.get(url,params=params)
                        if r.status_code in (429,500,502,503,504):time.sleep(2+attempt);continue
                        r.raise_for_status();raw=r.content;break
                    else:raise RuntimeError('Source unavailable: '+symbol)
                    cache.write_bytes(raw)
                response=json.loads(raw)['chart'];record=response['result'][0]
                if record.get('events',{}).get('splits'):raise ValueError('Unverified split adjustment: '+symbol)
                q=record['indicators']['quote'][0];rows=[];bad=0
                for i,ts in enumerate(record.get('timestamp',[])):
                    if not start<=ts<end:continue
                    values=[q[k][i] for k in ('open','high','low','close')]
                    if any(v is None for v in values):bad+=1;continue
                    o,h,l,c=map(float,values)
                    if not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:bad+=1;continue
                    rows.append({'ts':ts*1000,'open':o,'high':h,'low':l,'close':c})
                if plan.get('abort_on_invalid_rows') and bad:raise ValueError('Invalid daily quote rows: '+symbol)
                if len({r['ts'] for r in rows})!=len(rows):raise ValueError('Duplicate daily candles')
                dividends=[{'ts':v['date']*1000,'amount':v['amount']} for v in record.get('events',{}).get('dividends',{}).values()]
                data={'symbol':symbol,'kind':kind,'source':'Yahoo Finance daily indicative OHLC','url':url,'params':params,'raw_sha256':hashlib.sha256(raw).hexdigest(),'bars':rows,'dividends':dividends,'invalid_rows':bad,'timezone':record['meta'].get('exchangeTimezoneName')}
                file=args.out/(symbol.replace('=','_')+'.json');file.write_text(json.dumps(data,separators=(',',':'))+'\n');manifest['assets'][symbol]={'kind':kind,'file':file.name,'bars':len(rows),'invalid_rows':bad,'dividends':len(dividends),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()};print(symbol,len(rows),flush=True);time.sleep(.35)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
