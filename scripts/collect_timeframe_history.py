"""Checksum-verified public monthly one-minute crypto candles for broad timeframe research."""
import argparse,csv,hashlib,io,json,zipfile
from pathlib import Path
from datetime import datetime,timezone
import httpx
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True);args.cache.mkdir(parents=True,exist_ok=True)
    manifest={'source':'Binance public spot monthly1m archives','retrievedAt':datetime.now(timezone.utc).isoformat(),'files':[],'assets':{},'pocket_option_otc':False,'live_approved':False}
    with httpx.Client(timeout=45,follow_redirects=True) as client:
        for symbol in ('BTCUSDT','ETHUSDT','SOLUSDT'):
            batches=[]
            for year in (2025,2026):
                for month in range(1,13 if year==2025 else 11):
                    name=f'{symbol}-1m-{year}-{month:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/{name}';path=args.cache/name
                    response=client.get(url+'.CHECKSUM');response.raise_for_status();expected=response.text.split()[0].lower()
                    if path.exists():raw=path.read_bytes()
                    else:
                        response=client.get(url);response.raise_for_status();raw=response.content
                    digest=hashlib.sha256(raw).hexdigest()
                    if digest!=expected:raise ValueError('Archive checksum mismatch')
                    if not path.exists():path.write_bytes(raw)
                    rows=[]
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        members=[i for i in archive.infolist() if i.filename.endswith('.csv')]
                        if len(members)!=1 or members[0].file_size>50_000_000:raise ValueError('Unexpected source archive')
                        with archive.open(members[0]) as handle:
                            for row in csv.reader(io.TextIOWrapper(handle)):
                                ts=int(row[0]);ts=ts//1000 if ts>=10**14 else ts;o,h,l,c=map(float,row[1:5]);trades=int(row[8])
                                if ts%60000 or not all(np.isfinite([o,h,l,c])) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid source bar')
                                if trades>0:rows.append((ts,o,h,l,c))
                    batches.append(np.array(rows,dtype=np.float64));manifest['files'].append({'symbol':symbol,'year':year,'month':month,'url':url,'sha256':digest,'bars':len(rows),'checksumVerified':True});print(symbol,year,month,len(rows),flush=True)
            data=np.concatenate(batches);data=data[np.argsort(data[:,0])]
            if len(np.unique(data[:,0]))!=len(data):raise ValueError('Duplicate minute timestamps')
            output=args.out/(symbol+'.npy');np.save(output,data,allow_pickle=False);manifest['assets'][symbol]={'file':output.name,'bars':len(data),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
