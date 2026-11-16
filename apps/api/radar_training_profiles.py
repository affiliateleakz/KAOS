"""Market/horizon isolation and session-based outcomes for the local Radar trainer."""
import math
from datetime import timedelta
from hashlib import sha256
from kaos_opportunity import utc

FRAMES={'intraday':None,'daily':1,'weekly':5,'monthly':21}
GROUPS=('stock','crypto','forex')


def key(group,timeframe='intraday'):
    if group not in GROUPS or timeframe not in FRAMES:raise ValueError('Unsupported training profile')
    return group if timeframe=='intraday' else group+':'+timeframe


def outcome(row,history):
    """Count actual completed sessions after evidence was observed; never label back in time."""
    days=FRAMES[row['timeframe']]
    if row['source_at']>row['asof'] or not math.isfinite(row['price']) or row['price']<=0:return None
    prices=sorted((float(t),float(p)) for t,p in history if math.isfinite(float(t)) and math.isfinite(float(p)) and float(p)>0)
    if len({t for t,_ in prices})!=len(prices):return None
    if not any(t==row['source_at'] and abs(p/row['price']-1)<1e-6 for t,p in prices):return None
    future=[(t,p) for t,p in prices if t>row['asof']]
    if len(future)<days:return None
    selected=future[:days]
    timeline=[row['source_at']]+[t for t,_ in selected]
    if any(not 0<b-a<=5*86400 for a,b in zip(timeline,timeline[1:])):return None
    target,price=selected[-1]
    move=price/row['price']-1
    threshold=.0002 if row['group']=='forex' else .001
    return {'target_at':target,'forward_return':move,'label':int(move>0) if abs(move)>=threshold else None}


async def assess(native,asset,market,result,vector,now):
    frame=market['timeframe'];group=asset['asset_class'] if asset['asset_class'] in ('crypto','forex') else 'stock'
    profile=key(group,frame)
    base={**result,'model_state':'collecting','training_profile':profile,'timeframe':frame,
          'horizon':market.get('horizon',frame),'feature_values':dict(zip(native.FEATURES,vector)),'source_time':market.get('source_time'),
          'explanation':'Collecting observed evidence and later session outcomes for this market and timeframe.'}
    try:
        stamp=utc(market['source_time'])
        if not 0<=(now-stamp).total_seconds()<5*86400 or len(vector)!=len(native.FEATURES) or not all(math.isfinite(v) for v in vector):raise ValueError()
        if not math.isfinite(market['price']) or market['price']<=0:raise ValueError()
    except (TypeError,ValueError,KeyError):return {**base,'model_state':'market_unavailable'}
    history=market.get('closed_history',[])
    pending=await native.db.kaos_radar_samples.find({'group':group,'timeframe':frame,'schema':native.SCHEMA,'symbol':asset['symbol'],
        'label':{'$exists':False}}, {'_id':1,'timeframe':1,'group':1,'asof':1,'source_at':1,'price':1}).limit(100).to_list(100)
    for row in pending:
        label=outcome(row,history)
        if label is not None:await native.db.kaos_radar_samples.update_one({'_id':row['_id'],'label':{'$exists':False}},{'$set':label})
    identity=sha256(f"{native.SCHEMA}:{profile}:{asset['symbol']}:{stamp.timestamp()}".encode()).hexdigest()
    await native.db.kaos_radar_samples.update_one({'_id':identity},{'$setOnInsert':{
        'schema':native.SCHEMA,'group':group,'timeframe':frame,'profile':profile,'symbol':asset['symbol'],
        'source_at':stamp.timestamp(),'asof':now.timestamp(),'price':market['price'],'x':vector,
        'expires_at':now+timedelta(days=730)}},upsert=True)
    model=await native.db.kaos_radar_models.find_one({'_id':profile,'state':'active'})
    if not model:return base
    bundle=model.get('bundle',{})
    if bundle.get('profile')!=profile:return {**base,'model_state':'incompatible'}
    if not 0<=now.timestamp()-model.get('activated_at',0)<=30*86400 or not 0<now.timestamp()-bundle.get('trained_through',now.timestamp())<=90*86400:
        return {**base,'model_state':'expired'}
    try:p=native.probability(bundle,vector)
    except (ValueError,TypeError,KeyError,OverflowError):return {**base,'model_state':'incompatible'}
    direction='BUY' if p>=.6 else 'SELL' if p<=.4 else 'WAIT'
    values=[max(-8,min(8,(v-m)/s)) for v,m,s in zip(vector,bundle['means'],bundle['scales'])]
    factors=sorted([{'feature':n,'contribution':round(w*v,4)} for n,w,v in zip(native.FEATURES,bundle['weights'],values)],key=lambda r:abs(r['contribution']),reverse=True)[:5]
    return {**base,'model_state':'active','direction':direction,'priority':'medium' if direction!='WAIT' else 'low','model_score_up':round(p,4),
        'model_version':model.get('version'),'factors':factors,'feature_values':dict(zip(native.FEATURES,vector)),
        'explanation':f'KAOS local {profile} evidence model: {direction}. Closed-session research; revalidate before entry.'}
