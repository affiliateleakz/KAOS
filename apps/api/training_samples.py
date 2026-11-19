"""Mandatory, disclosed service learning; minimized, pseudonymous market observations only."""
import hashlib
import math
import re
from datetime import datetime, timezone, timedelta
from pymongo.errors import DuplicateKeyError
from db import db, new_id, now_iso

POLICY='kaos-service-learning-v1'
NOTICE='KAOS uses de-identified settled trade features and market outcomes to train personal, shared and owner models. Account credentials, payments, balances and raw screenshots are excluded.'
SCHEMA='kaos-binary-104-v1'
_indexes_ready=False

async def ensure_indexes():
    global _indexes_ready
    if _indexes_ready:return
    await db.ai_training_samples.create_index([('contributor',1),('scope',1),('decisionAt',-1)])
    await db.ai_training_samples.create_index('expiresAt',expireAfterSeconds=0)
    await db.ai_training_models.create_index([('owner',1),('audience',1),('scope',1),('state',1),('createdAt',-1)])
    await db.ai_training_jobs.create_index([('state',1),('createdAt',1)])
    _indexes_ready=True



def stamp(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool):return int(value if value>10**11 else value*1000)
    if isinstance(value,str):
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:raise ValueError('Timestamp must include a timezone')
        return int(parsed.timestamp()*1000)
    raise ValueError('A market decision timestamp is required')


def minimized(data, received_ms=None):
    """Whitelist fields, never persist arbitrary features dictionaries or free-text metadata."""
    received_ms=received_ms or int(datetime.now(timezone.utc).timestamp()*1000)
    features=data.get('features')
    vector=features.get('x',data.get('featureVector')) if isinstance(features,dict) else data.get('featureVector')
    if not isinstance(vector,list) or len(vector)!=104 or not all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1e12 for v in vector):raise ValueError('Require 104 finite canonical market features')
    platform={'pocketoption':'pocket_option'}.get(data.get('platform'),data.get('platform'))
    if platform!='pocket_option':raise ValueError('This feature schema is isolated to Pocket Option')
    timeframe=str(data.get('timeframe','5s'));expiration=str(data.get('expiration',''))
    if timeframe not in ('5','5s') or expiration not in ('15','15s','20','20s','25','25s','30','30s','45','45s','60','60s'):raise ValueError('Unsupported feature timeframe/expiry')
    seconds=int(expiration.rstrip('s'));asset=str(data.get('asset','')).upper()
    if not re.fullmatch(r'[A-Z0-9_/.\-]{2,32}',asset):raise ValueError('Invalid market symbol')
    outcome=str(data.get('outcome',data.get('result',''))).upper().replace('DRAW','TIE')
    direction=str(data.get('direction','')).upper()
    if outcome not in ('WIN','LOSS','TIE') or direction not in ('BUY','SELL'):raise ValueError('Require a settled trade direction and outcome')
    sample_type=data.get('sampleType','PAPER' if data.get('paper') else 'REAL')
    mode=data.get('accountMode')
    if sample_type not in ('REAL','PAPER') or mode not in ('REAL','DEMO') or (sample_type=='REAL')!=(mode=='REAL'):raise ValueError('Require a known matching real/demo account mode')
    settled=stamp(data.get('settledAt') or data.get('timestamp') or received_ms)
    decision=data.get('decisionAt')
    inferred=decision is None
    decision=settled-seconds*1000 if inferred else stamp(decision)
    if not 0<decision<settled<=received_ms+30000 or abs(settled-decision-seconds*1000)>5000:raise ValueError('Invalid decision/settlement timing')
    entry=data.get('entryPrice');exit=data.get('settlementPrice',data.get('exitPrice'))
    if not all(type(p) in (int,float) and math.isfinite(p) and p>0 for p in (entry,exit)):raise ValueError('Require actual entry and settlement prices')
    actual='TIE' if entry==exit else 'WIN' if (exit-entry)*(1 if direction=='BUY' else -1)>0 else 'LOSS'
    if actual!=outcome:raise ValueError('Outcome conflicts with recorded market prices')
    # Visual/account-derived context is excluded from shared fitting; canonical technical features remain.
    x=[float(v) for v in vector]
    for i in list(range(32,48))+[54,55]+list(range(88,104)):x[i]=0.0
    return {'schema':SCHEMA,'platform':platform,'asset':asset,'assetClass':'binary','timeframe':'5s','expirySeconds':seconds,'sampleType':sample_type,'accountMode':mode,'scope':f'pocket_option:binary:5s:{seconds}s:{sample_type.lower()}',
            'x':x,'label':None if outcome=='TIE' else int(exit>entry),'decisionAt':decision,'targetAt':settled,'timingQuality':'inferred' if inferred else 'explicit','outcome':outcome,'entryPrice':entry,'settlementPrice':exit,'trust':'member_reported','policy':POLICY}


async def ingest(user,data):
    record=minimized(data);await ensure_indexes();event=str(data.get('sampleId') or data.get('tradeId') or '')
    if not event or len(event)>160:raise ValueError('Stable trade/sample ID required')
    anon=user.get('learning_id')
    if not anon:
        # Deterministic opaque service identifier; never based on email, credentials or account balances.
        anon=hashlib.sha256(('kaos-learning:'+user['id']).encode()).hexdigest()
        await db.users.update_one({'id':user['id']},{'$set':{'learning_id':anon}})
    identity=hashlib.sha256(f"{anon}:{record['platform']}:{record['asset']}:{record['decisionAt']}:{record['expirySeconds']}:{record['sampleType']}".encode()).hexdigest()
    record.update(_id=identity,contributor=anon,id=new_id('learn'),createdAt=now_iso(),expiresAt=datetime.now(timezone.utc)+timedelta(days=90))
    try:
        result=await db.ai_training_samples.update_one({'_id':identity},{'$setOnInsert':record},upsert=True)
        return {'sampleId':event,'duplicate':result.upserted_id is None,'policy':POLICY,'sharedLearningRequired':True}
    except DuplicateKeyError:return {'sampleId':event,'duplicate':True,'policy':POLICY,'sharedLearningRequired':True}
