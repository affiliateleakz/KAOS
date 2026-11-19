from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,SecretStr,ConfigDict
from typing import Literal
from radar_training_profiles import key as profile_key,FRAMES
from auth import require_role
from db import db,now_iso
from services import audit_log
import radar_settings as settings

router=APIRouter(prefix='/api/admin/radar',tags=['radar-settings'])
owner=require_role('super_admin')
class ProviderInput(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool=True
 credentials:dict[str,SecretStr]=Field(default_factory=dict,max_length=6)

@router.get('/providers')
async def providers(admin=Depends(owner)):
 return {'vaultReady':settings.vault_ready(),'providers':[await settings.public_settings(p) for p in settings.VISIBLE_PROVIDERS]}

@router.post('/vault/initialize')
async def initialize(admin=Depends(owner)):
 settings.initialize_vault();await audit_log(admin,'radar_vault_initialized','radar')
 return {'vaultReady':True}

@router.put('/providers/{provider}')
async def save(provider:str,request:ProviderInput,admin=Depends(owner)):
 info=settings.CATALOG.get(provider)
 if not info:raise HTTPException(404,'Unknown research provider')
 if set(request.credentials)-set(info['fields']):raise HTTPException(400,'Unknown credential field')
 update={'enabled':request.enabled,'updatedAt':now_iso(),'updatedBy':admin['id']}
 changed=[]
 for name,secret in request.credentials.items():
  value=secret.get_secret_value().strip()
  if not value:continue
  if len(value)>8192:raise HTTPException(400,'Credential too long')
  update['encrypted.'+name]=settings.cipher().encrypt(value.encode()).decode();changed.append(name)
 await db.radar_provider_settings.update_one({'_id':provider},{'$set':update},upsert=True)
 await db.kaos_asset_reports.delete_many({})
 await db.kaos_opportunity_scans.delete_many({})
 await audit_log(admin,'radar_provider_saved','radar_provider',provider,{'credentialFieldsChanged':changed,'enabled':request.enabled})
 return await settings.public_settings(provider)


class TrainInput(BaseModel):
 model_config=ConfigDict(extra='forbid')
 group:str=Field(pattern=r'^(stock|crypto|forex)$')
 timeframe:Literal['intraday','daily','weekly','monthly']='intraday'


class ActivateInput(TrainInput):
 version:str=Field(min_length=1,max_length=80)


@router.get('/model')
async def model_status(admin=Depends(owner),timeframe:Literal['intraday','daily','weekly','monthly']='intraday'):
 from kaos_radar_ai import SCHEMA
 groups=[]
 for group in ('stock','crypto','forex'):
  profile=profile_key(group,timeframe)
  scope={'group':group,'schema':SCHEMA,'label':{'$in':[0,1]},'timeframe':timeframe if timeframe!='intraday' else {'$exists':False}}
  count=await db.kaos_radar_samples.count_documents(scope)
  active=await db.kaos_radar_models.find_one({'_id':profile})
  candidate=await db.kaos_radar_models.find_one({'_id':'candidate:'+profile})
  def public_model(row):
   if not row:return None
   compatible=row.get('bundle',{}).get('schema')==SCHEMA and (not row.get('bundle',{}).get('profile') if timeframe=='intraday' else row.get('bundle',{}).get('profile')==profile)
   clean={k:v for k,v in row.items() if k!='bundle'}
   if not compatible and clean.get('state') in ('active','candidate'):clean['state']='retraining_required'
   clean['compatible_schema']=compatible
   return clean
  active=public_model(active);candidate=public_model(candidate)
  groups.append({'group':group,'timeframe':timeframe,'profile':profile,'labeled_samples':count,'required_samples':120,
                 'active':active,'candidate':candidate})
 return {'engine':'KAOS Radar local evidence model','external_ai_service':False,'groups':groups,
         'timeframes':list(FRAMES),'binary_trainer':{'market':'Pocket Option binary','horizon':'30 seconds','admin_url':'/admin/kaos-ai','separate_schema':True},
         'learning':'Member scans and a separately deployed continuous worker save observed evidence; later closed candles label outcomes. Worker deployment is reported in the AI Control Center.'}


@router.post('/model/train')
async def train_model(request:TrainInput,admin=Depends(owner)):
 import asyncio
 import time
 from pymongo.errors import DuplicateKeyError
 from kaos_radar_ai import SCHEMA,train
 profile=profile_key(request.group,request.timeframe)
 stamp=time.time()
 try:
  await db.kaos_radar_model_locks.update_one({'_id':profile,'until':{'$lt':stamp}},
     {'$set':{'until':stamp+300}},upsert=True)
 except DuplicateKeyError:
  raise HTTPException(429,'Training has a five-minute cooldown per market group')
 rows=await db.kaos_radar_samples.find({'group':request.group,'schema':SCHEMA,'label':{'$in':[0,1]},'timeframe':request.timeframe if request.timeframe!='intraday' else {'$exists':False}},
    {'_id':0}).sort('asof',-1).limit(2000).to_list(2000)
 # Reduce correlated overlapping labels per ticker before the chronological split.
 spaced=[];last={}
 for row in sorted(rows,key=lambda r:r['asof']):
  if row['asof']<=last.get(row['symbol'],0):continue
  spaced.append(row);last[row['symbol']]=row['target_at']
 result=await asyncio.to_thread(train,spaced,profile if request.timeframe!='intraday' else None)
 version=now_iso()
 doc={**result,'version':version,'group':request.group,'timeframe':request.timeframe,'profile':profile,'trainedAt':version}
 await db.kaos_radar_models.update_one({'_id':'candidate:'+profile},{'$set':doc},upsert=True)
 await audit_log(admin,'radar_model_trained','radar_model',request.group,{'state':result['state']})
 return {k:v for k,v in doc.items() if k!='bundle'}


@router.post('/model/activate')
async def activate_model(request:ActivateInput,admin=Depends(owner)):
 import time
 from kaos_radar_ai import SCHEMA,FEATURES,probability
 profile=profile_key(request.group,request.timeframe)
 candidate=await db.kaos_radar_models.find_one({'_id':'candidate:'+profile,'version':request.version,'state':'candidate'})
 if (not candidate or candidate.get('bundle',{}).get('schema')!=SCHEMA
     or (bool(candidate.get('bundle',{}).get('profile')) if request.timeframe=='intraday' else candidate.get('bundle',{}).get('profile')!=profile)
     or not 0 < time.time()-candidate.get('bundle',{}).get('trained_through',0) <= (30 if request.timeframe=='intraday' else 90)*86400):
  raise HTTPException(409,'A matching candidate that passed validation is required')
 try:probability(candidate['bundle'],[0.0]*len(FEATURES))
 except (ValueError,TypeError,KeyError,OverflowError):raise HTTPException(409,'Candidate model bundle is invalid')
 active={k:v for k,v in candidate.items() if k!='_id'}
 active.update(state='active',activated_at=time.time())
 await db.kaos_radar_models.update_one({'_id':profile},{'$set':active},upsert=True)
 # Cached research reports must not hide a newly activated model.
 await db.kaos_radar_scans.update_many({}, {'$set':{'expires_at':now_iso()}})
 await db.kaos_asset_reports.delete_many({})
 await db.kaos_opportunity_scans.delete_many({})
 await audit_log(admin,'radar_model_activated','radar_model',request.group,{'version':request.version})
 return {'state':'active','version':request.version,'execution_enabled':False}
