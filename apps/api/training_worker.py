"""Dedicated continuous learning process, never started by Passenger or a web request."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import asyncio
import hashlib
import time
import logging
import uuid
from datetime import datetime,timezone,timedelta
from pymongo.errors import DuplicateKeyError
from db import db,now_iso
from training_samples import POLICY
from continuous_models import fit,prospective,eligible
from training_service import DEFAULT_SCOPE,contributor

log=logging.getLogger('kaos-training')


async def train_job(job):
    query={'policy':POLICY,'scope':job['scope'],'label':{'$in':[0,1]},'timingQuality':'explicit'}
    if job['audience']=='personal':query['contributor']=job['owner']
    rows=await db.ai_training_samples.find(query).sort('decisionAt',-1).limit(8000).to_list(8000)
    # Current accounts only; deleted/suspended contributors are excluded from new fitting.
    ids=list({r['contributor'] for r in rows})
    active=await db.users.find({'learning_id':{'$in':ids},'account_status':{'$nin':['suspended','banned','deleted']},'is_demo':{'$ne':True}},{'learning_id':1}).to_list(8000)
    allowed={r['learning_id'] for r in active};rows=[r for r in rows if r['contributor'] in allowed]
    used=eligible(rows,job['scope']);contributors={r['contributor'] for r in used}
    if job['audience']=='shared' and len(contributors)<3:
        result={'state':'collecting','samples':len(used),'reason':'Shared model requires three distinct current contributors'}
    else:result=await asyncio.to_thread(fit,rows,job['scope'],int(time.time()*1000))
    if result['state']=='collecting':
        await db.ai_training_jobs.update_one({'_id':job['_id']},{'$set':{'state':'completed','result':'collecting','samples':result.get('samples',0),'completedAt':now_iso()}})
        return 'collecting'
    key=hashlib.sha256(f"{job['owner']}:{job['audience']}:{job['scope']}:{result.get('datasetHash','collecting')}".encode()).hexdigest()
    # Retraining never overwrites an approved/published artifact or resets its validation clock.
    record={**result,'id':key,'version':key[:12],'owner':job['owner'],'audience':job['audience'],'scope':job['scope'],'createdAt':now_iso(),'contributors':sorted(contributors),'liveApproved':False}
    await db.ai_training_models.update_one({'_id':key},{'$setOnInsert':record},upsert=True)
    await db.ai_training_jobs.update_one({'_id':job['_id']},{'$set':{'state':'completed','result':result['state'],'modelId':key,'completedAt':now_iso()}})
    return result['state']


async def validate_candidates():
    rows=await db.ai_training_models.find({'state':'candidate'}).sort('prospectiveChecked',1).limit(5).to_list(5)
    for row in rows:
        query={'policy':POLICY,'scope':row['scope'],'decisionAt':{'$gt':row['trainedThrough']},'label':{'$in':[0,1]},'timingQuality':'explicit'}
        if row['audience']=='personal':query['contributor']=row['owner']
        fresh=await db.ai_training_samples.find(query).sort('decisionAt',1).limit(4000).to_list(4000)
        active=await db.users.find({'learning_id':{'$in':list({r['contributor'] for r in fresh})},'account_status':{'$nin':['suspended','banned','deleted']},'is_demo':{'$ne':True}},{'learning_id':1}).to_list(8000)
        allowed={r['learning_id'] for r in active};fresh=[r for r in fresh if r['contributor'] in allowed]
        result=await asyncio.to_thread(prospective,row,fresh)
        state='validated' if result['passed'] else 'prospective_failed' if result['actionableSamples']>=300 else 'expired' if time.time()*1000-row['createdAtMs']>30*86400000 else 'candidate'
        await db.ai_training_models.update_one({'_id':row['_id'],'state':'candidate'},{'$set':{'prospective':result,'state':state,'prospectiveChecked':time.time(),'validatedAt':now_iso() if result['passed'] else None}})


async def collect_radar(turn):
    """Observe evidence now; existing trainers later label from actual future closed candles."""
    from radar_research import context,asset_report
    from radar_trending import snapshot
    from radar_signals import market
    from types import SimpleNamespace
    frames=('intraday','daily','weekly','monthly');frame=frames[turn%4]
    from radar_opportunities import UNIVERSES
    assets=[{'symbol':UNIVERSES[market_name][(turn//4)%len(UNIVERSES[market_name])],'asset_class':kind} for market_name,kind in (('stocks','stock'),('crypto','crypto'),('forex','forex'))]
    evidence=await context(assets,budget=10);trending=await snapshot()
    reports=[]
    for asset in assets:
        quote=await market(SimpleNamespace(**asset),frame)
        reports.append(await asset_report(asset,evidence,trending,quote=quote))
    return {'timeframe':frame,'assets':len(reports),'states':[r.get('model_state') for r in reports]}


async def train_radar(turn):
    from routes_radar_admin import train_model,TrainInput
    groups=('stock','crypto','forex');frames=('intraday','daily','weekly','monthly')
    group=groups[turn%3];frame=frames[(turn//3)%4]
    return await train_model(TrainInput(group=group,timeframe=frame),{'id':'continuous-worker','role':'super_admin'})


async def cycle(collect=True):
    now=time.time();lease=uuid.uuid4().hex
    try:
        await db.ai_worker_locks.update_one({'_id':'continuous','until':{'$lt':now}},{'$set':{'until':now+300,'owner':lease}},upsert=True)
    except DuplicateKeyError:return {'state':'another_worker_running'}
    state=await db.ai_worker_state.find_one({'_id':'continuous'}) or {};turn=state.get('turn',0)
    result={'heartbeat':now,'turn':turn+1,'executionEnabled':False,'phase':'running','errors':[]}
    await db.ai_worker_state.update_one({'_id':'continuous'},{'$set':result},upsert=True)
    try:
        await validate_candidates()
        if collect:
            try:result['collection']=await asyncio.wait_for(collect_radar(turn),timeout=90)
            except Exception as exc:result['errors'].append({'task':'evidence','error':type(exc).__name__})
        job=await db.ai_training_jobs.find_one({'state':'queued'},sort=[('createdAt',1)])
        if job:
            try:result['training']=await train_job(job)
            except Exception as exc:
                await db.ai_training_jobs.update_one({'_id':job['_id']},{'$set':{'state':'failed','error':type(exc).__name__,'completedAt':now_iso()}})
                result['errors'].append({'task':'member_training','error':type(exc).__name__})
        # Rotate bounded research training; never activate a candidate automatically.
        if turn%12==0:
            try:result['radarTraining']=(await train_radar(turn//12)).get('state')
            except Exception as exc:result['errors'].append({'task':'radar_training','error':type(exc).__name__})
        if turn%72==0:
            slot=int(now//21600)
            scopes=await db.ai_training_samples.distinct('scope',{'policy':POLICY})
            scopes=sorted(set(scopes+[DEFAULT_SCOPE]))[:12]
            for audience,who in [('shared','shared')]+[('owner',contributor(u)) for u in await db.users.find({'role':'super_admin'},{'id':1,'learning_id':1}).limit(10).to_list(10)]:
                for scope in scopes:
                    key=f'{audience}:{who}:{scope}:{slot}'
                    await db.ai_training_jobs.update_one({'_id':key},{'$setOnInsert':{'id':key,'owner':who,'audience':audience,'scope':scope,'state':'queued','createdAt':now_iso()}},upsert=True)
        result.update(phase='waiting',heartbeat=time.time(),lastCompleted=now_iso())
        await db.ai_worker_state.update_one({'_id':'continuous'},{'$set':result},upsert=True)
        return result
    except Exception as exc:
        result.update(phase='error',heartbeat=time.time());result['errors'].append({'task':'cycle','error':type(exc).__name__})
        await db.ai_worker_state.update_one({'_id':'continuous'},{'$set':result},upsert=True)
        log.exception('Training cycle failed')
        return result
    finally:await db.ai_worker_locks.update_one({'_id':'continuous','owner':lease},{'$set':{'until':0}})


async def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--no-collect',action='store_true');args=p.parse_args()
    if os.getenv('KAOS_TRAINING_WORKER_ENABLED')!='true':raise RuntimeError('Enable only on the selected dedicated training host: KAOS_TRAINING_WORKER_ENABLED=true')
    await db.ai_training_samples.create_index([('scope',1),('decisionAt',1)])
    await db.ai_training_samples.create_index([('contributor',1),('scope',1)])
    while True:
        await cycle(not args.no_collect)
        if args.once:return
        await asyncio.sleep(max(60,int(os.getenv('KAOS_TRAINING_INTERVAL_SECONDS','300'))))

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO);asyncio.run(main())
