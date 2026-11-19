"""Download bounded public hourly archives; no broker credentials."""
import argparse,concurrent.futures,csv,hashlib,io,json,zipfile
from pathlib import Path
import httpx
import numpy as np
ASSETS=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT']

def fetch(job):
    asset,year,month,cache=job;name=f'{asset}-1h-{year}-{month:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/{asset}/1h/{name}';path=cache/name
    with httpx.Client(timeout=60,follow_redirects=True) as c:
        response=c.get(url+'.CHECKSUM');response.raise_for_status();expected=response.text.split()[0].lower()
        if path.exists():raw=path.read_bytes()
        else:
            response=c.get(url);response.raise_for_status();raw=response.content
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=expected:raise ValueError('Checksum mismatch')
        if not path.exists():path.write_bytes(raw)
    rows=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[i for i in z.infolist() if i.filename.endswith('.csv')]
        if len(files)!=1 or files[0].file_size>5_000_000:raise ValueError('Unexpected archive')
        with z.open(files[0]) as handle:
            for r in csv.reader(io.TextIOWrapper(handle)):
                ts=int(r[0]);ts=ts//1000 if ts>=10**14 else ts;o,h,l,close=map(float,r[1:5])
                if ts%3600000 or not np.isfinite([o,h,l,close]).all() or not 0<l<=min(o,close)<=max(o,close)<=h:raise ValueError('Invalid bar')
                if int(r[8])>0:rows.append((ts,o,h,l,close))
    return asset,rows,{'asset':asset,'year':year,'month':month,'url':url,'sha256':digest,'bars':len(rows),'checksumVerified':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);a.cache.mkdir(parents=True,exist_ok=True)
    jobs=[(asset,y,m,a.cache) for asset in ASSETS for y in range(2021,2026) for m in range(1,13)];data={s:[] for s in ASSETS};manifest={'files':[],'assets':{},'source':'Binance public spot1h','executionEnabled':False}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for count,(asset,rows,meta) in enumerate(pool.map(fetch,jobs),1):
            data[asset].extend(rows);manifest['files'].append(meta)
            if count%12==0:print('Verified',count,'of',len(jobs),'archives',flush=True)
    for asset,rows in data.items():
        arr=np.array(sorted(rows),dtype=float)
        if np.any(np.diff(arr[:,0])<=0):raise ValueError('Duplicate timestamps')
        path=a.out/(asset+'.npy');np.save(path,arr,allow_pickle=False);manifest['assets'][asset]={'file':path.name,'bars':len(arr),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
