"""Fixed four individual-stock snapshots for the requested supplemental test."""
import argparse,hashlib,json
from pathlib import Path
import httpx
from collect_all_in_one_history import get,ms

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);a.cache.mkdir(parents=True,exist_ok=True);manifest={'assets':{},'executionEnabled':False};start,end=ms('2025-01-01'),ms('2026-11-01')
    with httpx.Client(timeout=40,follow_redirects=True,headers={'User-Agent':'KAOS-research/1.0'}) as c:
        for symbol in ['AAPL','MSFT','NVDA','TSLA']:
            url='https://query1.finance.yahoo.com/v8/finance/chart/'+symbol;params={'period1':start//1000,'period2':end//1000,'interval':'1h','events':'div,splits','includePrePost':'false'};cached=a.cache/(symbol+'.json');raw=cached.read_bytes() if cached.exists() else get(c,url,params).content
            if not cached.exists():cached.write_bytes(raw)
            r=json.loads(raw)['chart']['result'][0];q=r['indicators']['quote'][0];periods=[p for day in r['meta'].get('tradingPeriods',[]) for p in day];bars=[];invalid=0
            if r.get('events',{}).get('splits'):
                manifest['assets'][symbol]={'excluded':'in-window split requires separate adjustment audit','source_sha256':hashlib.sha256(raw).hexdigest()};continue
            for i,t in enumerate(r.get('timestamp',[])):
                ts=int(t)*1000
                if not start<=ts<end:continue
                v=[q[k][i] for k in ['open','high','low','close']]
                if any(x is None for x in v):invalid+=1;continue
                o,h,l,close=map(float,v)
                if not 0<l<=min(o,close)<=max(o,close)<=h:invalid+=1;continue
                session=next((p for p in periods if p['start']*1000<=ts<p['end']*1000),None)
                if session is None:continue
                bars.append({'ts':ts,'end':min(ts+3600000,session['end']*1000),'open':o,'high':h,'low':l,'close':close,'session_start':session['start']*1000,'session_end':session['end']*1000})
            record={'symbol':symbol,'kind':'stocks','source':'Yahoo indicative regular-session hourly','source_url':url,'source_params':params,'source_sha256':hashlib.sha256(raw).hexdigest(),'bars':bars,'dividends':[{'ts':v['date']*1000,'amount':v['amount']} for v in r.get('events',{}).get('dividends',{}).values()],'invalid_rows':invalid};path=a.out/(symbol+'.json');path.write_text(json.dumps(record,separators=(',',':'))+'\n');manifest['assets'][symbol]={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bars':len(bars),'invalid_rows':invalid};print(symbol,len(bars),'invalid',invalid,flush=True)
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
