"""Public hourly stock/FX quotes and checksum-verified exchange crypto candles."""
import argparse,csv,hashlib,io,json,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
import httpx

ROOT=Path(__file__).resolve().parents[1]


def ms(day):return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)


def get(client,url,params=None):
    for attempt in range(3):
        r=client.get(url,params=params)
        if r.status_code in (429,500,502,503,504):time.sleep(1+attempt);continue
        r.raise_for_status();return r
    raise RuntimeError('Public data source unavailable: '+url)


def collect(out,cache):
    plan=json.loads((ROOT/'research/all_in_one_v1/plan.json').read_text());out.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    start,end=ms(plan['data_start']),ms(plan['data_end_exclusive']);manifest={'retrieved_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':hashlib.sha256((ROOT/'research/all_in_one_v1/plan.json').read_bytes()).hexdigest(),'assets':{},'files':[],'live_approved':False}
    with httpx.Client(timeout=40,follow_redirects=True,headers={'User-Agent':'KAOS-backtest-research/1.0'}) as client:
        for kind,symbols in [('stocks',plan['stock_symbols']),('forex',plan['forex_symbols'])]:
            for symbol in symbols:
                url='https://query1.finance.yahoo.com/v8/finance/chart/'+symbol
                path=cache/(symbol.replace('=','_')+'.yahoo.json');params={'period1':start//1000,'period2':end//1000,'interval':'1h','events':'div,splits','includePrePost':'false'}
                payload=path.read_bytes() if path.exists() else get(client,url,params).content
                if not path.exists():path.write_bytes(payload)
                result=json.loads(payload)['chart']['result'][0];q=result['indicators']['quote'][0];periods=[p for day in result['meta'].get('tradingPeriods',[]) for p in day] if kind=='stocks' else []
                bars=[];invalid=0;outside=0
                for i,t in enumerate(result.get('timestamp',[])):
                    ts=int(t)*1000
                    if not start<=ts<end:outside+=1;continue
                    vals=[q[k][i] for k in ('open','high','low','close')]
                    if any(v is None for v in vals):invalid+=1;continue
                    o,h,l,c=map(float,vals)
                    if not 0<l<=min(o,c)<=max(o,c)<=h:invalid+=1;continue
                    finish=ts+3600000;session_start=None;session_end=None
                    if kind=='stocks':
                        period=next((p for p in periods if p['start']*1000<=ts<p['end']*1000),None)
                        if not period:outside+=1;continue
                        session_start=period['start']*1000;session_end=period['end']*1000;finish=min(finish,session_end)
                    if finish>end:continue
                    bars.append({'ts':ts,'end':finish,'open':o,'high':h,'low':l,'close':c,'session_start':session_start,'session_end':session_end})
                if result.get('events',{}).get('splits'):raise ValueError('Split handling needs separate verification for '+symbol)
                dividends=[{'ts':v['date']*1000,'amount':v['amount']} for v in result.get('events',{}).get('dividends',{}).values()]
                record={'symbol':symbol,'kind':kind,'source':'Yahoo Finance indicative hourly history','source_url':url,'source_params':params,'source_sha256':hashlib.sha256(payload).hexdigest(),'timezone':result['meta'].get('exchangeTimezoneName'),'bars':bars,'dividends':dividends,'invalid_rows':invalid,'outside_window_or_session':outside}
                output=out/(symbol.replace('=','_')+'.json');output.write_text(json.dumps(record,separators=(',',':'))+'\n');manifest['assets'][symbol]={'kind':kind,'bars':len(bars),'file':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'invalid_rows':invalid,'dividends':len(dividends)};print(symbol,len(bars),flush=True);time.sleep(.2)
        for symbol in plan['crypto_symbols']:
            bars=[];year,month=2025,1
            while (year,month)<(2026,11):
                name=f'{symbol}-1h-{year}-{month:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{name}';path=cache/name
                expected=get(client,url+'.CHECKSUM').text.split()[0].lower();payload=path.read_bytes() if path.exists() else get(client,url).content
                if hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('Checksum mismatch')
                if not path.exists():path.write_bytes(payload)
                with zipfile.ZipFile(io.BytesIO(payload)) as z:
                    file=next(n for n in z.namelist() if n.endswith('.csv'))
                    for row in csv.reader(io.StringIO(z.read(file).decode())):
                        ts=int(row[0]);ts=ts//1000 if ts>=10**14 else ts
                        if not start<=ts<end:continue
                        o,h,l,c=map(float,row[1:5]);trades=int(row[8])
                        if ts%3600000 or not 0<l<=min(o,c)<=max(o,c)<=h or trades<=0:raise ValueError('Invalid exchange hourly bar')
                        bars.append({'ts':ts,'end':ts+3600000,'open':o,'high':h,'low':l,'close':c,'session_start':None,'session_end':None})
                manifest['files'].append({'url':url,'sha256':expected,'verified':True});month+=1
                if month==13:year+=1;month=1
                time.sleep(.08)
            if len({b['ts'] for b in bars})!=len(bars):raise ValueError('Duplicate exchange bars')
            record={'symbol':symbol,'kind':'crypto','source':'Binance spot monthly hourly archives','bars':sorted(bars,key=lambda b:b['ts']),'dividends':[]}
            output=out/(symbol+'.json');output.write_text(json.dumps(record,separators=(',',':'))+'\n');manifest['assets'][symbol]={'kind':'crypto','bars':len(bars),'file':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()};print(symbol,len(bars),flush=True)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('History collection complete',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();collect(a.out,a.cache)
