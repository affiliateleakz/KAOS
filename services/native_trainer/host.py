"""KAOS Chrome native messaging host. Reads/writes length-prefixed JSON on stdio."""
import sys,json,struct,math,traceback

def send(obj):
    b=json.dumps(obj,separators=(',',':'),allow_nan=False).encode('utf8')
    sys.stdout.buffer.write(struct.pack('<I',len(b))+b)
    sys.stdout.buffer.flush()

def convert_tree(node):
    if 'leaf' in node: return {'leaf':float(node['leaf'])}
    f=int(node['split'][1:]) if str(node['split']).startswith('f') else int(node['split'])
    # XGBoost split uses <; JS uses <=, move boundary one floating point ULP lower.
    t=math.nextafter(float(node['split_condition']),-math.inf)
    kids={int(c['nodeid']):c for c in node['children']}
    yes=int(node['yes']);no=int(node['no']);missing=int(node['missing'])
    return {'f':f,'t':t,'l':convert_tree(kids[yes]),'r':convert_tree(kids[no])}

def train(req):
    import numpy as np
    import xgboost as xgb
    rows=[]
    for r in req.get('samples',[]):
        if not isinstance(r,dict) or not isinstance(r.get('x'),list) or len(r['x']) != 104:continue
        if r.get('label') not in (0,1):continue
        try:
            x=np.asarray(r['x'],dtype=np.float32)
            if not np.all(np.isfinite(x)):continue
            rows.append((float(r.get('t') or 0),str(r.get('asset') or ''),x,int(r['label'])))
        except (ValueError,TypeError):continue
    rows.sort(key=lambda v:v[0]);n=len(rows)
    if n<100:return {'ok':False,'status':'warming','samples':n,'message':'Need 100 valid labeled 104-feature samples'}
    split=int(n*.8)
    X=np.stack([r[2] for r in rows]);y=np.asarray([r[3] for r in rows]);
    if len(set(y[:split]))<2:return {'ok':False,'status':'warming','samples':n,'message':'Training requires both UP and DOWN labels'}
    # Group by candle timestamp at boundary to avoid overlapping duplicate timestamps.
    while split>int(n*.65) and rows[split-1][0]==rows[split][0]:split-=1
    if split<=int(n*.65):return {'ok':False,'status':'warming','samples':n,'message':'Insufficient distinct timestamps for chronological holdout'}
    # Purge training observations whose future outcome overlaps the test window.
    # Timestamps are milliseconds in the extension; use request horizon as a guard.
    horizon=max(0,int(req.get('targetHorizonMs') or 30000))
    test_start=rows[split][0]
    train_end=split
    while train_end>0 and rows[train_end-1][0]+horizon>=test_start:
        train_end-=1
    if train_end<100 or train_end<int(n*.5):
        return {'ok':False,'status':'warming','samples':n,'message':'Not enough chronological training observations after label-overlap purge'}
    # Reject duplicate (asset,timestamp) observations to prevent artificially inflated
    # confidence intervals when the same candle appears more than once.
    test_keys=[(r[1],r[0]) for r in rows[split:]]
    if len(test_keys)!=len(set(test_keys)):
        return {'ok':False,'status':'rejected','samples':n,'message':'Duplicate asset/timestamp observations in holdout; deduplicate before training'}
    model=xgb.XGBClassifier(n_estimators=35,max_depth=3,learning_rate=.06,subsample=.8,colsample_bytree=.85,objective='binary:logistic',tree_method='hist',n_jobs=2,random_state=42)
    model.fit(X[:train_end],y[:train_end]);probs=model.predict_proba(X[split:])[:,1]
    acc=float(np.mean((probs>=.5)==y[split:]));tracc=float(np.mean(model.predict(X[:train_end])==y[:train_end]))
    # Do not deploy a model merely because fitting succeeded. Evaluate on unseen data.
    holdout=y[split:]
    baseline=float(max(np.mean(holdout),1-np.mean(holdout)))
    n_holdout=len(holdout)
    # Confidence bound guards against a small, lucky holdout.
    import math as _math
    z=1.96
    wilson=(acc+z*z/(2*n_holdout)-z*_math.sqrt((acc*(1-acc)+z*z/(4*n_holdout))/n_holdout))/(1+z*z/n_holdout)
    report={'samples':n,'trainSamples':train_end,'purgedSamples':split-train_end,'holdoutSamples':n_holdout,'holdoutAccuracy':acc,'trainAccuracy':tracc,'majorityBaseline':baseline,'wilsonLower95':wilson,'featureCount':104,'targetHorizonMs':req.get('targetHorizonMs',30000),'perAsset':{}}
    # Promotion is stricter than fitting: enough independent holdout observations,
    # better than trivial majority guessing, and positive statistical evidence.
    if n_holdout < 200 or acc <= baseline or wilson <= .5:
        return {'ok':False,'status':'rejected','report':report,'message':'Candidate rejected: insufficient unseen evidence; existing model retained'}
    booster=model.get_booster();trees=[convert_tree(json.loads(t)) for t in booster.get_dump(dump_format='json')]
    # XGB JSON tree leaves already include learning rate; logistic base margin is logit(base_score).
    conf=json.loads(booster.save_config());base_score=float(str(conf['learner']['learner_model_param']['base_score']).strip('[]'))
    base=math.log(base_score/(1-base_score))
    return {'ok':True,'status':'trained','model':{'features':104,'base':base,'trees':trees,'totalSamples':train_end},'report':report,'message':'Chronological holdout; no guarantee of trading profitability'}

def train_multi(req):
    """Train independent horizon models; never promote on training score alone.

    Each observation must contain its own completed-expiry label and horizon.
    This avoids relabeling one outcome as though it applied to every expiry.
    """
    from collections import defaultdict
    groups=defaultdict(list)
    allowed={5000,10000,15000,20000,25000,30000,60000}
    for row in req.get('samples',[]):
        if not isinstance(row,dict): continue
        try: horizon=int(row.get('targetHorizonMs',row.get('horizonMs',0)))
        except (TypeError,ValueError):continue
        if horizon in allowed:groups[horizon].append(row)
    results={}
    for horizon in sorted(groups):
        subset=groups[horizon]
        # A model is only comparable with other models trained for this same expiry.
        outcome=train({'samples':subset,'targetHorizonMs':horizon})
        results[str(horizon)]={'status':outcome.get('status'),'ok':bool(outcome.get('ok')),
                               'report':outcome.get('report'), 'message':outcome.get('message')}
        if outcome.get('ok'):
            results[str(horizon)]['model']=outcome['model']
    return {'ok':True,'status':'evaluated','models':results,'horizonsEvaluated':len(results),
            'message':'Each expiry independently evaluated; rejected models are not deployable.'}

def train_specialists(req):
    """Separate validated models by known setup family AND actual expiry.

    No family inferred from the future outcome; unknown observations are skipped.
    Rejected candidates never enter the deployable result set.
    """
    from collections import defaultdict
    allowed={'REVERSAL','RUNNER','BREAKOUT'}
    horizons={5000,10000,15000,20000,25000,30000,60000}
    groups=defaultdict(list)
    for row in req.get('samples',[]):
        if not isinstance(row,dict) or row.get('specialist') not in allowed:continue
        try:h=int(row.get('targetHorizonMs',0))
        except (TypeError,ValueError):continue
        if h in horizons:groups[(row['specialist'],h)].append(row)
    results={}
    for (family,h),rows in sorted(groups.items()):
        outcome=train({'samples':rows,'targetHorizonMs':h})
        result={'status':outcome.get('status'),'ok':bool(outcome.get('ok')),
                'report':outcome.get('report'),'message':outcome.get('message')}
        if outcome.get('ok'):result['model']=outcome['model']
        results[f'{family}:{h}']=result
    return {'ok':True,'status':'evaluated','models':results,'horizonsEvaluated':len(results),
            'message':'Research-only specialist evaluation; no live-trade authorization.'}

def main():
    while True:
        hdr=sys.stdin.buffer.read(4)
        if len(hdr)!=4:break
        length=struct.unpack('<I',hdr)[0]
        if length>50_000_000:send({'ok':False,'error':'Message too large'});break
        buf=sys.stdin.buffer.read(length)
        if len(buf)!=length:break
        try:
            req=json.loads(buf)
            send(train(req) if req.get('type')=='train_xgboost' else train_multi(req) if req.get('type')=='train_multi_expiry' else train_specialists(req) if req.get('type')=='train_specialists' else {'ok':False,'error':'Unsupported message type'})
        except Exception as exc:
            send({'ok':False,'status':'error','error':str(exc)})
if __name__=='__main__':main()
