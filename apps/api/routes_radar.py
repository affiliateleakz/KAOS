"""Member-triggered multi-source research scan; no orders or execution authority."""
import asyncio
import json
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict,field_validator
from pymongo import ReturnDocument,UpdateOne
from pymongo.errors import DuplicateKeyError
from db import db
from routes_opportunity import member,Observation
from radar_sources import Sources,LABELS
import radar_settings

router=APIRouter(prefix='/api/v1/intelligence',tags=['research-scan'])
KINDS=Literal['stock','etf','option','crypto','dex','forex','future']
PROVIDERS=Literal['news','market','sec','ethereum','government']
class Asset(BaseModel):
 model_config=ConfigDict(extra='forbid')
 symbol:str=Field(pattern=r'^[A-Za-z][A-Za-z0-9.]{0,11}$')
 asset_class:KINDS
 @field_validator('symbol')
 @classmethod
 def uppercase(cls,value):return value.upper()
class ScanInput(BaseModel):
 model_config=ConfigDict(extra='forbid')
 assets:list[Asset]=Field(min_length=1,max_length=5)
 sources:list[PROVIDERS]=Field(default_factory=lambda:[p for p in LABELS if p not in ('reddit','x','bluesky','facebook')],min_length=1,max_length=9)
 include_ai:bool=True
@router.get('/scan/status')
async def scan_status(user=Depends(member)):
 providers=[await radar_settings.public_settings(p) for p in radar_settings.VISIBLE_PROVIDERS]
 return {'providers':[{k:v for k,v in p.items() if k!='fields'} for p in providers],
         'ai_engine':'KAOS Radar local evidence model','external_ai_service':False,'maximum_assets':5,'cache_seconds':300,'automatic_background_worker':False,
         'coverage':'Selected watchlist and connected source samples, plus recent stored collector observations',
         'research_only':True,'trade_execution_enabled':False}

def evidence_id(row):return sha256((row['source']+':'+row['event_id']).encode()).hexdigest()[:20]

def balanced_evidence(evidence,limit):
 groups={}
 for row in evidence:groups.setdefault((row['asset'],row['asset_class'],row['source'],row.get('provider',row['source'])),[]).append(row)
 selected=[]
 while len(selected)<limit:
  changed=False
  for rows in groups.values():
   if rows:selected.append(rows.pop(0));changed=True
   if len(selected)>=limit:break
  if not changed:break
 return selected

from kaos_radar_ai import analyze, SCHEMA

async def collect(assets,sources,settings):
 session=Sources(settings);jobs={}
 try:
  started=asyncio.get_running_loop().time()
  try:await asyncio.wait_for(session.prepare(sources),timeout=8)
  except asyncio.TimeoutError:pass
  for provider in sources:
   for asset in assets:
    task=asyncio.create_task(session.run(provider,asset));jobs[task]=(provider,asset)
  remaining=max(.05,24-(asyncio.get_running_loop().time()-started))
  done,pending=await asyncio.wait(jobs,timeout=remaining)
  results=[task.result() for task in jobs if task in done]
  for task in pending:
   task.cancel();provider,asset=jobs[task]
   results.append({'provider':provider,'name':LABELS[provider],'asset':asset['symbol'],'asset_class':asset['asset_class'],'state':'time_budget','message':'Source did not finish within this bounded scan; no zero-mention assumption','observations':None,'records':[]})
  if pending:await asyncio.gather(*pending,return_exceptions=True)
  return results
 finally:
  for task in jobs:
   if not task.done():task.cancel()
  if jobs:await asyncio.gather(*jobs,return_exceptions=True)
  await session.close()

@router.post('/scan')
async def scan(request:ScanInput,user=Depends(member)):
 assets=list({(a.symbol,a.asset_class):a.model_dump() for a in request.assets}.values());sources=list(dict.fromkeys(request.sources))
 if len({a['symbol'] for a in assets})!=len(assets):raise HTTPException(422,'Use each symbol once per scan')
 settings=dict(zip(radar_settings.VISIBLE_PROVIDERS,await asyncio.gather(*(radar_settings.settings(p) for p in radar_settings.VISIBLE_PROVIDERS))))
 context=[];trending=None
 if request.include_ai:
  from radar_trending import snapshot
  trending=await snapshot()
  models=await asyncio.gather(*(db.kaos_radar_models.find_one({'_id':group,'state':'active'}) for group in ('stock','crypto')))
  context=[trending.get('fetched_at'),trending.get('state'),trending.get('stale'),[(model or {}).get('version') for model in models]]
 version=sha256(json.dumps([settings,context],sort_keys=True).encode()).hexdigest()+SCHEMA
 key=sha256(json.dumps([user['id'],assets,sources,request.include_ai,version],sort_keys=True).encode()).hexdigest()
 now=datetime.now(timezone.utc);stamp=now.isoformat()
 cached=await db.kaos_radar_scans.find_one({'_id':key})
 if cached and cached.get('expires_at','')>stamp and cached.get('result'):return {**cached['result'],'cached':True}
 try:
  await db.kaos_radar_scans.find_one_and_update({'_id':key,'$or':[{'lease_until':{'$lte':stamp}},{'lease_until':{'$exists':False}}]},
    {'$set':{'lease_until':(now+timedelta(seconds=90)).isoformat(),'user_id':user['id'],'started_at':stamp}},upsert=True,return_document=ReturnDocument.AFTER)
 except DuplicateKeyError:raise HTTPException(409,'This scan is already running; wait before starting it again') from None
 try:
  try:
   await db.kaos_radar_limits.find_one_and_update({'_id':user['id'],'$or':[{'next_at':{'$lte':stamp}},{'next_at':{'$exists':False}}]},
    {'$set':{'next_at':(now+timedelta(seconds=60)).isoformat()}},upsert=True,return_document=ReturnDocument.AFTER)
  except DuplicateKeyError:raise HTTPException(429,'Wait one minute between new watchlist scans; cached reports can still be reopened') from None
  results=await collect(assets,sources,settings)
  allowed={(a['symbol'],a['asset_class']) for a in assets}
  valid={};writes=[]
  for result in results:
   for row in result.pop('records',[]):
    try:
     item=Observation(**row);record=item.model_dump(mode='json')
     published=datetime.fromisoformat(record['published_at']);observed=datetime.fromisoformat(record['observed_at'])
     if published>observed or observed>datetime.now(timezone.utc) or (record['asset'],record['asset_class']) not in allowed:continue
    except (ValueError,TypeError):continue
    record['provider']=str(row.get('provider',result['provider']))[:40];record['id']=evidence_id(record)
    valid[record['id']]=record
    writes.append(UpdateOne({'_id':'radar:'+record['id']},{'$set':{k:v for k,v in record.items() if k!='id'}},upsert=True))
  if writes:await db.kaos_intelligence.bulk_write(writes,ordered=False)
  previous=await db.kaos_intelligence.find({'asset':{'$in':[a['symbol'] for a in assets]},'observed_at':{'$gte':(now-timedelta(days=7)).isoformat()}},{'_id':0}).sort('observed_at',-1).limit(200).to_list(200)
  allowed={(a['symbol'],a['asset_class']) for a in assets}
  for row in previous:
   if (row.get('asset'),row.get('asset_class')) not in allowed:continue
   try:normalized=Observation(**row).model_dump(mode='json')
   except (ValueError,TypeError):continue
   if datetime.fromisoformat(normalized['published_at'])>datetime.fromisoformat(normalized['observed_at']) or datetime.fromisoformat(normalized['observed_at'])>datetime.now(timezone.utc):continue
   normalized['id']=evidence_id(normalized);normalized['provider']=str(row.get('provider',row['source']))[:40]
   valid.setdefault(normalized['id'],normalized)
  evidence=balanced_evidence(sorted(valid.values(),key=lambda r:r['published_at'],reverse=True),120)
  ai=await analyze(assets,evidence,results,settings,trending) if request.include_ai else {'state':'not_requested','message':'AI analysis was not requested'}
  report={'analysis_engine':'kaos-local-v1','assets':assets,'completed_at':datetime.now(timezone.utc).isoformat(),'source_status':results,'evidence':evidence,'ai':ai,'cached':False,
          'coverage':'Selected watchlist/source samples and recent stored collector observations','research_only':True,'trade_execution_enabled':False}
  await db.kaos_radar_scans.update_one({'_id':key},{'$set':{'result':report,'lease_until':stamp,'expires_at':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}})
  await db.kaos_radar_scans.delete_many({'user_id':user['id'],'expires_at':{'$lt':(now-timedelta(days=7)).isoformat()}})
  return report
 except Exception:
  await db.kaos_radar_scans.update_one({'_id':key},{'$set':{'lease_until':stamp}})
  raise


@router.get('/scan/latest')
async def latest_scan(user=Depends(member)):
 rows=await db.kaos_radar_scans.find({'user_id':user['id'],'result':{'$exists':True},'result.analysis_engine':'kaos-local-v1'},{'_id':0,'result':1}).sort('started_at',-1).limit(1).to_list(1)
 return {'scan':rows[0]['result'] if rows else None}
