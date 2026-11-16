"""Private member models, published shared models, and a separate owner training audience."""
import hashlib
import time
from fastapi import APIRouter,Depends,HTTPException,Request,Query
from pydantic import BaseModel,Field
from db import db,now_iso
from auth import get_current_user,require_role
from services_trading import get_entitlements
from training_samples import POLICY,NOTICE

router=APIRouter(prefix='/api/v1/ai/training',tags=['continuous-learning'])
admin_router=APIRouter(prefix='/api/admin/ai/continuous',tags=['continuous-learning-admin'])
owner=require_role('super_admin')
DEFAULT_SCOPE='pocket_option:binary:5s:20s:real'


def contributor(user):return user.get('learning_id') or hashlib.sha256(('kaos-learning:'+user['id']).encode()).hexdigest()


class TrainRequest(BaseModel):
    scope:str=Field(default=DEFAULT_SCOPE,pattern=r'^pocket_option:binary:5s:(15|20|25|30|45|60)s:(real|paper)$')


def public_model(row):
    if not row:return None
    return {k:row.get(k) for k in ('id','scope','audience','state','samples','metrics','prospective','createdAt','trainedThrough','version','liveApproved')}


async def worker_status():
    row=await db.ai_worker_state.find_one({'_id':'continuous'},{'_id':0}) or {}
    heartbeat=row.get('heartbeat',0)
    return {**row,'running':0<=time.time()-heartbeat<900,'configured':bool(row),'notice':'A separate training worker must be deployed; web requests never start it.'}


@router.get('/status')
async def status(user=Depends(get_current_user)):
    ent=await get_entitlements(user);who=contributor(user)
    own=await db.ai_training_models.find({'owner':who,'audience':{'$in':['personal','owner']} if user.get('role')=='super_admin' else 'personal'},{'_id':0,'bundle':0}).sort('createdAt',-1).limit(12).to_list(12)
    shared=[]
    if ent.get('pretrainedModels'):
        shared=await db.ai_training_models.find({'audience':'shared','state':'published'},{'_id':0,'bundle':0,'contributors':0,'owner':0}).sort('createdAt',-1).limit(12).to_list(12)
    count=await db.ai_training_samples.count_documents({'contributor':who,'policy':POLICY})
    jobs=await db.ai_training_jobs.find({'owner':who},{'_id':0,'owner':0}).sort('createdAt',-1).limit(5).to_list(5)
    return {'policy':POLICY,'notice':NOTICE,'sharedLearningRequired':True,'personalTraining':bool(ent.get('aiTraining')),'pretrainedAccess':bool(ent.get('pretrainedModels')),'personalModels':[public_model(r) for r in own],'sharedModels':[public_model(r) for r in shared],'personalSamples':count,'jobs':jobs,'worker':{k:v for k,v in (await worker_status()).items() if k in ('running','configured','notice')},'executionEnabled':False,'minimumSamples':500}


async def enqueue(who,audience,scope):
    slot=int(time.time()//3600)
    key=hashlib.sha256(f'{who}:{audience}:{scope}:{slot}'.encode()).hexdigest()
    await db.ai_training_jobs.update_one({'_id':key},{'$setOnInsert':{'id':key,'owner':who,'audience':audience,'scope':scope,'state':'queued','createdAt':now_iso()}},upsert=True)
    existing=await db.ai_training_jobs.find_one({'_id':key})
    return {'jobId':key,'state':existing['state'] if existing else 'queued','executionEnabled':False}


@router.post('/train')
async def queue_personal(req:TrainRequest,user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get('aiTraining'):raise HTTPException(403,'Personal AI training requires Pro or Ultimate')
    return await enqueue(contributor(user),'personal',req.scope)


@admin_router.get('/status')
async def admin_status(user=Depends(owner)):
    models=await db.ai_training_models.find({}, {'_id':0,'bundle':0,'contributors':0,'owner':0}).sort('createdAt',-1).limit(40).to_list(40)
    return {'worker':await worker_status(),'models':[public_model(r) for r in models],'policy':POLICY,'notice':NOTICE,'externalAIService':False,'executionEnabled':False}


@admin_router.post('/owner/train')
async def queue_owner(req:TrainRequest,user=Depends(owner)):
    return await enqueue(contributor(user),'owner',req.scope)


@admin_router.post('/publish/{model_id}')
async def publish(model_id:str,user=Depends(owner)):
    row=await db.ai_training_models.find_one({'id':model_id,'audience':'shared','state':'validated'})
    if not row or not row.get('prospective',{}).get('passed') or not row.get('metrics',{}).get('passed'):
        raise HTTPException(409,'A shared model with passed chronological and later prospective validation is required')
    if not 0<=time.time()-row['createdAtMs']/1000<30*86400:raise HTTPException(409,'Model is stale')
    await db.ai_training_models.update_one({'id':model_id,'state':'validated'},{'$set':{'state':'published','publishedAt':now_iso(),'publishedBy':user['id']}})
    return {'state':'published','executionEnabled':False}


async def bundle(scope:str=DEFAULT_SCOPE,source:str='auto',user=Depends(get_current_user)):
    ent=await get_entitlements(user);who=contributor(user)
    if not ent.get('aiTraining'):raise HTTPException(403,'AI models require Pro or Ultimate')
    if source not in ('auto','personal','shared','owner'):raise HTTPException(422,'Choose a supported model source')
    if source=='shared' and not ent.get('pretrainedModels'):raise HTTPException(403,'Pretrained models require Ultimate')
    if source=='owner' and user.get('role')!='super_admin':raise HTTPException(403,'Owner model access required')
    row=None
    if source=='auto' and user.get('role')=='super_admin':
        row=await db.ai_training_models.find_one({'audience':'owner','owner':who,'scope':scope,'state':'validated'},{'_id':0},sort=[('createdAt',-1)])
    if row is None and (source=='shared' or source=='auto' and ent.get('pretrainedModels')):
        row=await db.ai_training_models.find_one({'audience':'shared','scope':scope,'state':'published'},{'_id':0},sort=[('createdAt',-1)])
    if row is None and source in ('auto','personal','owner'):
        row=await db.ai_training_models.find_one({'audience':'owner' if source=='owner' else 'personal','owner':who,'scope':scope,'state':'validated'},{'_id':0},sort=[('createdAt',-1)])
    if row and not 0<=time.time()-row['createdAtMs']/1000<30*86400:row=None
    return {'available':bool(row),'member':who,'source':row['audience'] if row else source,'model':{**row['bundle'],'researchOnly':True} if row else None,'modelId':row.get('id') if row else None,'scope':scope,'policy':POLICY,'personalTraining':bool(ent.get('aiTraining')),'pretrainedAccess':bool(ent.get('pretrainedModels')),'executionEnabled':False,'state':'ready' if row else 'untrained_or_awaiting_validation'}


async def predict_for_member(user,features,scope=DEFAULT_SCOPE):
    selected=await bundle(scope,'auto',user)
    if not selected['available']:
        return {'source':'AI','direction':'HOLD','confidence':0,'probUp':None,'modelVersion':None,'authority':'LEARNING_ONLY','simulated':False,'productionTrained':False,'available':False,'live':False,'reason':selected['state']}
    import kaos_ai_infer
    try:pred=kaos_ai_infer.predict(selected['model'],features)
    except (ValueError,TypeError,IndexError,KeyError) as exc:raise HTTPException(422,'Invalid canonical feature vector') from exc
    return {'source':'AI','direction':pred['direction'],'confidence':pred['confidence'],'probUp':pred['prob_up'],'modelVersion':selected['modelId'],'modelKind':'native-xgboost','authority':'LEARNING_ONLY','simulated':False,'productionTrained':True,'available':True,'live':False,'expiration':str(selected['model']['targetHorizonMs']//1000)+'s'}


@router.get('/bundle')
async def download_bundle(request:Request,scope:str=Query(default=DEFAULT_SCOPE,pattern=r'^pocket_option:binary:5s:(15|20|25|30|45|60)s:(real|paper)$'),source:str='auto',user=Depends(get_current_user)):
    device=request.headers.get('X-Device-Id')
    if device:
        record=await db.devices.find_one({'installId':device,'userId':user['id']})
        if not record or record.get('revoked'):raise HTTPException(403,'Authorized installation required')
    return await bundle(scope,source,user)
