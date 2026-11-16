"""Chronological, purged binary training. No automatic publishing or order authority."""
import math
from hashlib import sha256
import json
from signature_backtest import wilson

MIN_SAMPLES=500
MAX_SAMPLES=4000


def eligible(rows,scope):
    result=[];last={};seen=set()
    for row in sorted(rows,key=lambda r:r.get('decisionAt',0)):
        x=row.get('x');start=row.get('decisionAt',0);end=row.get('targetAt',0)
        if (row.get('scope')!=scope or row.get('schema')!='kaos-binary-104-v1' or row.get('label') not in (0,1)
            or row.get('timingQuality')!='explicit' or not isinstance(x,list) or len(x)!=104
            or not all(type(v) in (int,float) and math.isfinite(v) for v in x) or not 0<start<end or row.get('expirySeconds') not in (15,20,25,30,45,60) or not isinstance(row.get('asset'),str)):continue
        # Same market/time across members is the same observation, not independent evidence.
        key=(row.get('asset'),start//(row['expirySeconds']*1000))
        if key in seen or start<last.get(row['asset'],0):continue
        seen.add(key);last[row['asset']]=end;result.append(row)
    return result[-MAX_SAMPLES:]


def fit(rows,scope,now_ms):
    rows=[r for r in eligible(rows,scope) if r['targetAt']<=now_ms]
    if len(rows)<MIN_SAMPLES:return {'state':'collecting','samples':len(rows),'required':MIN_SAMPLES}
    import numpy as np
    import kaos_ai_trainer as native
    cut=rows[int(len(rows)*.7)]['decisionAt']
    training=[r for r in rows if r['targetAt']<cut];held=[r for r in rows if r['decisionAt']>=cut]
    if len(training)<300 or len(held)<100 or any(sum(r['label']==v for r in training)<50 for v in (0,1)) or any(sum(r['label']==v for r in held)<20 for v in (0,1)):
        return {'state':'collecting','samples':len(rows),'reason':'Need enough purged history and both directions'}
    X=native.model_matrix([(r['decisionAt'],r['asset'],np.asarray(r['x'],dtype=np.float32),r['label']) for r in training]);Y=np.asarray([r['label'] for r in training])
    model=native.XGBClassifier(n_estimators=40,max_depth=2,learning_rate=.03,subsample=.8,colsample_bytree=.7,min_child_weight=8,reg_lambda=12,reg_alpha=.5,objective='binary:logistic',eval_metric='logloss',random_state=47,n_jobs=1,tree_method='hist')
    model.fit(X,Y)
    # Export the model's actual trained intercept, not a guessed library default.
    cfg=json.loads(model.get_booster().save_config());base=cfg['learner']['learner_model_param']['base_score']
    if isinstance(base,str):base=float(base.strip('[]').split(',')[0])
    base=max(1e-7,min(1-1e-7,float(base)))
    bundle={'type':'xgboost','task':'logit_sum','features':104,'base':math.log(base/(1-base)),'trees':[native.xgb_tree(json.loads(t)) for t in model.get_booster().get_dump(dump_format='json')],'targetHorizonMs':rows[0]['expirySeconds']*1000,'trainedSamples':len(training),'totalSamples':len(rows),'scope':scope,'schema':'kaos-binary-104-v1'}
    import kaos_ai_infer
    preds=[kaos_ai_infer.predict(bundle,r['x'],r['asset'])['prob_up'] for r in held]
    metrics=evaluate(preds,held)
    return {'state':'candidate' if metrics['passed'] else 'validation_failed','scope':scope,'bundle':bundle,'samples':len(rows),'trainingEnd':max(r['targetAt'] for r in training),'trainedThrough':max(r['targetAt'] for r in rows),'holdoutStart':cut,'metrics':metrics,'datasetHash':sha256(json.dumps([(r['_id'],r['label']) for r in rows]).encode()).hexdigest(),'createdAtMs':now_ms,'liveApproved':False}


def evaluate(predictions,rows,payout=.8):
    chosen=[(p,r) for p,r in zip(predictions,rows) if p>=.6 or p<=.4]
    wins=sum((p>=.5)==r['label'] for p,r in chosen);n=len(chosen)
    baseline=max(sum(r['label']==v for r in rows) for v in (0,1))/len(rows) if rows else 1
    accuracy=sum((p>=.5)==r['label'] for p,r in zip(predictions,rows))/len(rows) if rows else 0
    lower=wilson(wins,n)
    return {'holdoutSamples':len(rows),'actionableSamples':n,'wins':wins,'accuracy':accuracy,'majorityBaseline':baseline,'winRate':wins/n if n else None,'wilsonLower95':lower,'assumedPayout':payout,'breakEven':1/(1+payout),'passed':n>=100 and accuracy>baseline and lower>1/(1+payout),'profitabilityVerified':False}


def prospective(model,rows):
    import kaos_ai_infer
    import time
    fresh=[r for r in eligible(rows,model['scope']) if r['decisionAt']>model['trainedThrough'] and r['targetAt']<=int(time.time()*1000)]
    probabilities=[kaos_ai_infer.predict(model['bundle'],r['x'],r['asset'])['prob_up'] for r in fresh]
    return evaluate(probabilities,fresh)
