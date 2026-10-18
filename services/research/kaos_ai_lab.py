"""KAOS 1.7 research-only candle archive and AI notebook. No broker orders or LLM calls."""
import json, math, os, re, tempfile, threading, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'kaos_research_data'
LOCK=threading.RLock()

def _asset(value):
    value=str(value).strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]{2,40}',value): raise ValueError('invalid market')
    return value

def _period(value):
    value=int(value)
    if value not in (5,15,30,60,300,900,3600): raise ValueError('unsupported candle timeframe')
    return value

def _save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.kaos-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            json.dump(data,f,separators=(',',':'),allow_nan=False)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def ingest(payload):
    market=_asset(payload['market']);tf=_period(payload['timeframe'])
    incoming=payload['candles']
    if not isinstance(incoming,list) or not 1<=len(incoming)<=20000:raise ValueError('1-20000 candles required')
    rows=[]
    for x in incoming:
        if not isinstance(x,dict):raise ValueError('invalid candle')
        t=int(x.get('time',x.get('timestamp',-1)))
        if t<1000000000 or t>4102444800:raise ValueError('invalid candle time')
        c={k:float(x[k]) for k in ('open','high','low','close')}
        if any(not math.isfinite(v) or v<=0 for v in c.values()):raise ValueError('invalid price')
        if not c['low']<=min(c['open'],c['close'])<=max(c['open'],c['close'])<=c['high']:raise ValueError('invalid OHLC')
        rows.append({'time':t,**c,'volume':float(x.get('volume',0))})
    path=ROOT/'candles'/f'{market}_{tf}s.json'
    with LOCK:
        old=json.loads(path.read_text()) if path.exists() else []
        merged={r['time']:r for r in old}
        for r in rows:merged[r['time']]=r
        result=sorted(merged.values(),key=lambda r:r['time'])
        _save(path,result)
    gaps=sum(b['time']-a['time']>tf for a,b in zip(result,result[1:]))
    return {'market':market,'timeframe':tf,'received':len(rows),'stored':len(result),'gaps':gaps,'oldest':result[0]['time'],'newest':result[-1]['time'],'trade_authorized':False}

def list_archive():
    base=ROOT/'candles'
    return [{'name':p.stem,'count':len(json.loads(p.read_text()))} for p in sorted(base.glob('*.json'))] if base.exists() else []

def notebook(payload):
    agent=_asset(payload.get('agent','research'))
    title=str(payload.get('title','')).strip()[:100]
    if not title:raise ValueError('title required')
    # Do not store secrets, raw auth frames, or API keys in research notes.
    notes=str(payload.get('notes',''))[:3000]
    if re.search(r'(?i)(sk-[A-Za-z0-9_-]{12,}|PO_SSID|OPENAI_API_KEY|42\[\s*"auth")',notes):raise ValueError('notes appear to contain credentials')
    path=ROOT/'notebooks'/f'{agent}.json'
    with LOCK:
        data=json.loads(path.read_text()) if path.exists() else []
        item={'time':int(time.time()),'title':title,'notes':notes,'status':str(payload.get('status','untested'))[:40], 'trade_authorized':False}
        data.append(item);_save(path,data[-500:])
    return {'saved':True,'agent':agent,'entries':len(data),'trade_authorized':False}

def read_notebook(agent):
    agent=_asset(agent);path=ROOT/'notebooks'/f'{agent}.json'
    return json.loads(path.read_text()) if path.exists() else []
