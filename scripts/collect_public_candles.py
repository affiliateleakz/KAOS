"""Checksum-verified Binance public 1s klines -> complete observed 5s research bars."""
import argparse,csv,hashlib,io,json,math,time,zipfile
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import httpx

BASE='https://data.binance.vision/data/spot/daily/klines'


def aggregate(data):
    groups={};seen=set();source_rows=0;empty_seconds=0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members=[m for m in archive.infolist() if m.filename.endswith('.csv')]
        if len(members)!=1 or members[0].file_size>40_000_000:raise ValueError('Unexpected source CSV')
        with archive.open(members[0]) as handle:
            for row in csv.reader(io.TextIOWrapper(handle)):
                ts=int(row[0]);ts=ts//1000 if ts>=10**14 else ts
                o,h,l,c,volume=map(float,row[1:6]);trades=int(row[8])
                if ts in seen or ts%1000 or not all(math.isfinite(v) for v in (o,h,l,c,volume)) or not 0<l<=min(o,c)<=max(o,c)<=h or volume<0 or trades<0:raise ValueError('Invalid or duplicate source second')
                seen.add(ts);source_rows+=1;empty_seconds+=trades==0
                bucket=ts//5000*5000
                groups.setdefault(bucket,[]).append((ts,o,h,l,c,volume,trades))
    bars=[];incomplete=0;empty_buckets=0
    for ts,values in sorted(groups.items()):
        values.sort()
        if [r[0] for r in values]!=[ts+i*1000 for i in range(5)]:incomplete+=1;continue
        trades=sum(r[6] for r in values)
        if trades==0:empty_buckets+=1;continue
        bars.append({'ts':ts,'closeTs':ts+5000,'open':values[0][1],'high':max(r[2] for r in values),'low':min(r[3] for r in values),'close':values[-1][4],'volume':sum(r[5] for r in values),'trades':trades})
    return bars,{'source_seconds':source_rows,'empty_source_seconds':empty_seconds,'incomplete_five_second_buckets':incomplete,'no_trade_buckets_excluded':empty_buckets,'bars':len(bars)}


def download(client,url):
    for attempt in range(4):
        response=client.get(url)
        if response.status_code in (429,500,502,503,504):
            time.sleep(min(8,2**attempt));continue
        response.raise_for_status();return response.content
    raise RuntimeError('Public archive temporarily unavailable')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--start',type=date.fromisoformat,required=True);parser.add_argument('--days',type=int,default=7);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);args=parser.parse_args()
    if not 1<=args.days<=31:parser.error('Use 1–31 bounded days')
    if args.start+timedelta(days=args.days)>datetime.now(timezone.utc).date():parser.error('Use completed UTC days')
    args.out.mkdir(parents=True,exist_ok=True);args.cache.mkdir(parents=True,exist_ok=True)
    manifest={'provider':'Binance public spot daily archive','source_interval':'1s','output_interval':'5s','start_utc':str(args.start),'days':args.days,'retrieved_at':datetime.now(timezone.utc).isoformat(),'collector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':[],'markets':{},'broker_execution_verified':False,'pocket_option_otc':False,'no_trade_buckets':'excluded, never filled','license_source':'https://github.com/binance/binance-public-data','live_approved':False}
    with httpx.Client(timeout=60,follow_redirects=True,headers={'User-Agent':'KAOS-offline-research/1.0'}) as client:
        for symbol in ('BTCUSDT','ETHUSDT','SOLUSDT'):
            bars=[]
            for offset in range(args.days):
                day=args.start+timedelta(days=offset);name=f'{symbol}-1s-{day}.zip';url=f'{BASE}/{symbol}/1s/{name}';cached=args.cache/name
                checksum=download(client,url+'.CHECKSUM').decode().split()[0].lower()
                if len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):raise ValueError('Invalid source checksum')
                payload=cached.read_bytes() if cached.exists() else download(client,url)
                actual=hashlib.sha256(payload).hexdigest()
                if actual!=checksum:raise ValueError('Source checksum mismatch: '+name)
                if not cached.exists():cached.write_bytes(payload)
                rows,quality=aggregate(payload);bars.extend(rows)
                manifest['files'].append({'symbol':symbol,'date':str(day),'url':url,'checksum_url':url+'.CHECKSUM','sha256':actual,'checksum_verified':True,**quality})
                print(symbol,day,quality,flush=True);time.sleep(.15)
            if len({r['ts'] for r in bars})!=len(bars):raise ValueError('Duplicate output candles')
            output=args.out/(symbol+'_5s.json');output.write_text(json.dumps({'markets':{symbol:bars},'source':manifest['provider'],'timeframe':'5s','pocket_option_otc':False},separators=(',',':'))+'\n')
            manifest['markets'][symbol]={'bars':len(bars),'start_ts':bars[0]['ts'] if bars else None,'end_ts':bars[-1]['ts'] if bars else None,'file':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    package=args.out/'KAOS-Public-Crypto-5s.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(args.out.glob('*.json')):archive.write(file,file.name)
    print(json.dumps({'package':str(package),'bytes':package.stat().st_size,'markets':manifest['markets']}),flush=True)

if __name__=='__main__':main()
