#!/usr/bin/env python3
"""AlphaBot native XGBoost trainer.

V24.1.235: canonical 104-feature market + visual schema; accepts legacy 88-feature rows by padding 16 neutral values.
- Global model uses all valid fresh labeled rows.
- Per-asset models are trained when an asset has enough balanced history.
- Time-ordered holdout is retained.
- Class imbalance is weighted so one-sided markets do not force a permanent BUY/SELL bias.
"""
import json, sys, math, re
from collections import defaultdict
import numpy as np
from xgboost import XGBClassifier
try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except Exception:
    LGBMClassifier = None
    HAS_LIGHTGBM = False
from sklearn.metrics import accuracy_score

FEATURES = 104

# V24.1.106 GENERALIZATION MASK
# Keep the 88-feature wire/storage schema for compatibility, but neutralize
# the most redundant hand-score block (32-47) and clock-only features (54-55)
# before fitting. This reduces memorization without deleting existing samples.
MODEL_DISABLED_FEATURES = tuple(list(range(32,48)) + [54,55])

def model_matrix(rows):
    X = np.vstack([r[2] for r in rows]).astype(np.float32, copy=True)
    if X.size and MODEL_DISABLED_FEATURES:
        X[:, MODEL_DISABLED_FEATURES] = 0.0
    return X
MAX_TRAIN_ROWS = 2000
MIN_XGB_SAMPLES = 12
MIN_ASSET_MODEL_SAMPLES = 80
MIN_CHAMPION_HOLDOUT = 50



def wilson_interval(correct, total, z=1.96):
    n=int(total or 0)
    if n<=0: return (0.0,1.0)
    k=max(0,min(n,int(correct or 0)))
    p=k/n; z2=z*z; den=1.0+z2/n
    center=(p+z2/(2*n))/den
    margin=(z*math.sqrt((p*(1-p)+z2/(4*n))/n))/den
    return (max(0.0,center-margin),min(1.0,center+margin))

def accuracy_ci(y_true, pred):
    n=len(y_true)
    if n<=0: return (0.0,0,0.0,1.0)
    correct=int((np.asarray(y_true)==np.asarray(pred)).sum())
    acc=correct/n; low,high=wilson_interval(correct,n)
    return (float(acc),correct,float(low),float(high))

def xgb_tree(node):
    if 'leaf' in node:
        return {'leaf': float(node['leaf'])}
    kids = {int(c['nodeid']): c for c in node.get('children', [])}
    yes, no = int(node['yes']), int(node['no'])
    return {
        'f': int(str(node['split']).lstrip('f')),
        't': float(node['split_condition']),
        'l': xgb_tree(kids[yes]),
        'r': xgb_tree(kids[no])
    }


def base_margin_for(model):
    try:
        raw_base = model.get_params().get('base_score', 0.5)
        if isinstance(raw_base, str):
            m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', raw_base)
            base_prob = float(m.group(0)) if m else 0.5
        else:
            base_prob = float(raw_base)
        base_prob = min(1-1e-6, max(1e-6, base_prob))
        return math.log(base_prob/(1-base_prob))
    except Exception:
        return 0.0


def fit_rows(rows, target_horizon_ms, now_ms=0):
    rows = sorted(rows, key=lambda r: r[0])
    if len(rows) < MIN_XGB_SAMPLES:
        return None, {'status':'warming','samples':len(rows),'message':f'Collecting XGBoost data: {len(rows)}/{MIN_XGB_SAMPLES} labeled samples.'}, None
    y_all = np.asarray([r[3] for r in rows], dtype=np.int8)
    if len(np.unique(y_all)) < 2:
        return None, {'status':'warming','samples':len(rows),'message':'Need both UP and DOWN outcomes.'}, None

    cut = max(4, min(len(rows)-2, int(len(rows)*0.75)))
    train_rows, test_rows = rows[:cut], rows[cut:]
    ytr = np.asarray([r[3] for r in train_rows], dtype=np.int8)
    if len(np.unique(ytr)) < 2:
        cut = max(4, len(rows)//2)
        train_rows, test_rows = rows[:cut], rows[cut:]
        ytr = np.asarray([r[3] for r in train_rows], dtype=np.int8)
    if len(np.unique(ytr)) < 2:
        return None, {'status':'warming','samples':len(rows),'message':'Training window has one class.'}, None

    Xtr = model_matrix(train_rows)
    # V24.1.112: reserve the latter half of the chronological OOS tail for
    # champion selection. Reported holdout uses only the earlier OOS slice.
    split_oos=max(1,len(test_rows)//2)
    report_rows=test_rows[:split_oos]
    selection_reserve=test_rows[split_oos:]
    Xte = model_matrix(report_rows)
    yte = np.asarray([r[3] for r in report_rows], dtype=np.int8)

    # Balance UP/DOWN learning while keeping chronological data intact.
    pos = max(1, int((ytr == 1).sum()))
    neg = max(1, int((ytr == 0).sum()))
    class_w = np.where(ytr == 1, len(ytr)/(2*pos), len(ytr)/(2*neg)).astype(np.float32)

    # Mild recency emphasis: newest training rows matter somewhat more, but old
    # regimes are still retained so the model remembers bull/bear/range behavior.
    recency_w = np.linspace(0.80, 1.20, len(ytr), dtype=np.float32)
    sample_w = class_w * recency_w

    n_estimators = int(max(20, min(48, 16 + len(Xtr)//10)))
    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=2,
        learning_rate=0.03,
        subsample=0.72,
        colsample_bytree=0.50,
        min_child_weight=max(2.0, min(6.0, len(Xtr)/24.0)),
        gamma=0.03,
        reg_lambda=10.0,
        reg_alpha=0.50,
        objective='binary:logistic',
        eval_metric='logloss',
        random_state=42,
        n_jobs=2,
        tree_method='hist'
    )
    model.fit(Xtr, ytr, sample_weight=sample_w)
    pred = (model.predict_proba(Xte)[:,1] >= .5).astype(int)
    train_pred = (model.predict_proba(Xtr)[:,1] >= .5).astype(int)
    dump = [json.loads(t) for t in model.get_booster().get_dump(dump_format='json')]
    bundle = {
        'type': 'xgboost',
        'version': 5,
        'features': FEATURES,
        'task': 'logit_sum',
        'base': float(base_margin_for(model)),
        'trees': [xgb_tree(t) for t in dump],
        'trainedSamples': int(len(Xtr)),
        'totalSamples': int(len(rows)),
        'targetHorizonMs': int(target_horizon_ms),
        'generatedAt': int(now_ms or 0)
    }
    hold_acc, hold_correct, hold_low, hold_high = accuracy_ci(yte, pred)
    report = {
        'samples': len(rows),
        'trainSamples': len(Xtr),
        'trainingCutoffTs': int(train_rows[-1][0]) if train_rows else 0,
        'selectionStartTs': int(selection_reserve[0][0]) if selection_reserve else 0,
        'selectionReserveSamples': len(selection_reserve),
        'holdoutSamples': len(Xte),
        'trainAccuracy': float(accuracy_score(ytr, train_pred)),
        'holdoutAccuracy': hold_acc,
        'holdoutCorrect': hold_correct,
        'holdoutWilsonLow': hold_low,
        'holdoutWilsonHigh': hold_high,
        'upSamples': int((y_all == 1).sum()),
        'downSamples': int((y_all == 0).sum()),
        'modelActiveFeatures': FEATURES-len(MODEL_DISABLED_FEATURES),
        'modelDisabledFeatures': list(MODEL_DISABLED_FEATURES)
    }
    return bundle, report, model



def lgb_tree(node):
    if 'leaf_value' in node:
        return {'leaf': float(node['leaf_value'])}
    return {
        'f': int(node.get('split_feature', 0)),
        't': float(node.get('threshold', 0.0)),
        'l': lgb_tree(node.get('left_child') or {'leaf_value':0.0}),
        'r': lgb_tree(node.get('right_child') or {'leaf_value':0.0})
    }

def fit_lightgbm_rows(rows, target_horizon_ms, now_ms=0):
    if not HAS_LIGHTGBM:
        return None, {'status':'unavailable','message':'lightgbm package is not installed'}, None
    rows = sorted(rows, key=lambda r: r[0])
    if len(rows) < MIN_XGB_SAMPLES:
        return None, {'status':'warming','samples':len(rows)}, None
    y_all=np.asarray([r[3] for r in rows],dtype=np.int8)
    if len(np.unique(y_all))<2: return None, {'status':'warming','samples':len(rows)}, None
    cut=max(4,min(len(rows)-2,int(len(rows)*0.75)))
    tr,te=rows[:cut],rows[cut:]
    ytr=np.asarray([r[3] for r in tr],dtype=np.int8)
    if len(np.unique(ytr))<2:
        cut=max(4,len(rows)//2); tr,te=rows[:cut],rows[cut:]; ytr=np.asarray([r[3] for r in tr],dtype=np.int8)
    if len(np.unique(ytr))<2: return None, {'status':'warming','samples':len(rows)}, None
    split_oos=max(1,len(te)//2); report_te=te[:split_oos]; selection_reserve=te[split_oos:]; Xtr=model_matrix(tr); Xte=model_matrix(report_te); yte=np.asarray([r[3] for r in report_te],dtype=np.int8)
    pos=max(1,int((ytr==1).sum())); neg=max(1,int((ytr==0).sum()))
    class_w=np.where(ytr==1,len(ytr)/(2*pos),len(ytr)/(2*neg)).astype(np.float32)
    recency_w=np.linspace(.80,1.20,len(ytr),dtype=np.float32); sw=class_w*recency_w
    n_estimators=int(max(20,min(48,16+len(Xtr)//10)))
    m=LGBMClassifier(n_estimators=n_estimators,num_leaves=5,max_depth=2,learning_rate=.025,subsample=.72,colsample_bytree=.50,min_child_samples=max(10,min(24,len(Xtr)//6)),reg_lambda=10.0,reg_alpha=.50,objective='binary',random_state=43,n_jobs=2,verbosity=-1)
    m.fit(Xtr,ytr,sample_weight=sw)
    pred=(m.predict_proba(Xte)[:,1]>=.5).astype(int); train_pred=(m.predict_proba(Xtr)[:,1]>=.5).astype(int)
    dm=m.booster_.dump_model(); trees=[lgb_tree(t['tree_structure']) for t in dm.get('tree_info',[])]
    bundle={'type':'lightgbm','version':2,'features':FEATURES,'task':'logit_sum','base':0.0,'trees':trees,'trainedSamples':len(Xtr),'totalSamples':len(rows),'targetHorizonMs':int(target_horizon_ms),'generatedAt':int(now_ms or 0)}
    hold_acc,hold_correct,hold_low,hold_high=accuracy_ci(yte,pred)
    rep={'samples':len(rows),'trainSamples':len(Xtr),'trainingCutoffTs':int(tr[-1][0]) if tr else 0,'selectionStartTs':int(selection_reserve[0][0]) if selection_reserve else 0,'selectionReserveSamples':len(selection_reserve),'holdoutSamples':len(Xte),'trainAccuracy':float(accuracy_score(ytr,train_pred)),'holdoutAccuracy':hold_acc,'holdoutCorrect':hold_correct,'holdoutWilsonLow':hold_low,'holdoutWilsonHigh':hold_high,'upSamples':int((y_all==1).sum()),'downSamples':int((y_all==0).sum()),'modelActiveFeatures':FEATURES-len(MODEL_DISABLED_FEATURES),'modelDisabledFeatures':list(MODEL_DISABLED_FEATURES)}
    return bundle,rep,m

def main(msg):
    if not isinstance(msg, dict) or msg.get('type') != 'train_xgboost':
        return {'ok': False, 'error': 'invalid training request'}
    # Legacy model has one fixed 30-second target. Reject other horizons
    # instead of silently training a mislabeled global classifier.
    target = int(msg.get('targetHorizonMs', 30000))
    if target != 30000:
        return {'ok': False, 'error': 'legacy_trainer_requires_30s_horizon'}
    raw = msg.get('samples') or []
    # This compatibility trainer must never mix explicit sources/timeframes.
    # Mixed training belongs to the versioned multi-horizon research pipeline.
    scopes = set()
    for sample in raw:
        if not isinstance(sample, dict):
            continue
        if sample.get('targetHorizonMs') not in (None, 30000):
            return {'ok': False, 'error': 'sample_horizon_mismatch'}
        scopes.add((str(sample.get('source', 'legacy')),
                    str(sample.get('timeframe', 'legacy'))))
    if len(scopes) > 1:
        return {'ok': False, 'error': 'mixed_source_or_timeframe'}
    rows = []
    seen = set()
    rejected_feature_lengths = {}
    rejected_missing_label = 0
    for row_index, s in enumerate(raw[-MAX_TRAIN_ROWS:]):
        x = s.get('x') if isinstance(s, dict) else None
        y = s.get('label') if isinstance(s, dict) else None
        if y is None:
            rejected_missing_label += 1
            continue
        if isinstance(x, list) and len(x) == 88:
            # V219 backward compatibility: historical market/indicator samples
            # have no video context, so their 16 visual features are neutral.
            x = x + [0.0] * 16
        if not isinstance(x, list) or len(x) != FEATURES:
            k = 'non-list' if not isinstance(x, list) else str(len(x))
            rejected_feature_lengths[k] = rejected_feature_lengths.get(k, 0) + 1
            continue
        try:
            # Accept both current `t` and older/synthetic `ts` timestamp fields.
            # Never collapse an entire imported dataset to one row merely because
            # a timestamp field is missing.
            raw_t = s.get('t', s.get('ts', 0))
            t = int(raw_t or 0)
            asset = str(s.get('asset', 'UNKNOWN'))
            # V24.1.112: one truly independent row per asset per 30s target candle,
            # regardless of whether JS tagged it setup/paper/trade or timestamps differ by ms.
            bucket = (t // 30000) * 30000 if t else 0
            key = (asset, bucket) if bucket else ('row', row_index, asset)
            if key in seen:
                continue
            seen.add(key)
            xx = np.nan_to_num(np.asarray(x, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
            yy = 1 if float(y) >= .5 else 0
            rows.append((t, asset, xx, yy))
        except Exception:
            continue

    raw_valid_count = len(raw)
    target = int(msg.get('targetHorizonMs', 30000))
    now_ms = int(msg.get('now', 0) or 0)
    global_model, global_report, global_sklearn = fit_rows(rows, target, now_ms)
    if global_model is None:
        if len(rows) == 0 and raw:
            detail = ''
            if rejected_feature_lengths:
                detail = f' Feature-length mismatch: trainer expects {FEATURES}; received {rejected_feature_lengths}.'
            return {'ok': False, **global_report, 'expectedFeatures': FEATURES,
                    'receivedSamples': len(raw), 'rejectedFeatureLengths': rejected_feature_lengths,
                    'rejectedMissingLabel': rejected_missing_label,
                    'message': str(global_report.get('message','')) + detail}
        return {'ok': False, **global_report}
    lgb_global, lgb_global_report, lgb_global_sklearn = fit_lightgbm_rows(rows, target, now_ms)

    grouped = defaultdict(list)
    for r in rows:
        grouped[r[1]].append(r)

    asset_models = {}
    lgb_asset_models = {}
    per_asset = {}
    for asset, arows in grouped.items():
        labels = {r[3] for r in arows}
        if len(arows) < MIN_ASSET_MODEL_SAMPLES or len(labels) < 2:
            per_asset[asset] = {
                'samples': len(arows), 'trained': False,
                'reason': f'need {MIN_ASSET_MODEL_SAMPLES}+ samples and both directions'
            }
            continue
        model, rep, local_sklearn = fit_rows(arows, target, now_ms)
        lgb_model, lgb_rep, lgb_local_sklearn = fit_lightgbm_rows(arows, target, now_ms)
        if lgb_model is not None: lgb_asset_models[asset] = lgb_model
        if model is not None:
            asset_models[asset] = model

            # V24.1.65 CHAMPION/CHALLENGER: compare the local model with the
            # global model on the EXACT SAME chronological asset holdout.
            # This prevents a young market model from replacing a stronger
            # global model merely because the local model exists.
            ordered = sorted(arows, key=lambda r: r[0])
            local_cut_ts=int(rep.get('trainingCutoffTs',0) or 0)
            local_selection_start=int(rep.get('selectionStartTs',0) or 0)
            global_cut_ts=int(global_report.get('trainingCutoffTs',0) or 0)
            clean_cut=max(local_cut_ts,global_cut_ts)
            selection_rows=[r for r in ordered if int(r[0] or 0)>=local_selection_start and int(r[0] or 0)>clean_cut] if local_selection_start else []
            global_holdout_acc = None
            local_selection_acc = None
            lgb_global_same = None
            lgb_local_selection_acc = None
            if selection_rows:
                Xcmp=model_matrix(selection_rows)
                ycmp=np.asarray([r[3] for r in selection_rows],dtype=np.int8)
                if global_sklearn is not None:
                    gpred=(global_sklearn.predict_proba(Xcmp)[:,1]>=.5).astype(int)
                    global_holdout_acc=float(accuracy_score(ycmp,gpred))
                if local_sklearn is not None:
                    lpred=(local_sklearn.predict_proba(Xcmp)[:,1]>=.5).astype(int)
                    local_selection_acc=float(accuracy_score(ycmp,lpred))
                if lgb_global_sklearn is not None:
                    gp=(lgb_global_sklearn.predict_proba(Xcmp)[:,1]>=.5).astype(int)
                    lgb_global_same=float(accuracy_score(ycmp,gp))
                if lgb_local_sklearn is not None:
                    lp=(lgb_local_sklearn.predict_proba(Xcmp)[:,1]>=.5).astype(int)
                    lgb_local_selection_acc=float(accuracy_score(ycmp,lp))
            selection_n=len(selection_rows)

            local_acc = float(rep.get('holdoutAccuracy', 0.0) or 0.0)
            hold_n = int(rep.get('holdoutSamples', 0) or 0)
            sample_n = int(rep.get('samples', len(arows)) or len(arows))
            advantage = None if global_holdout_acc is None else float(local_acc - global_holdout_acc)
            local_correct=int(round(local_acc*hold_n)); local_low,_=wilson_interval(local_correct,hold_n)
            global_correct=int(round((global_holdout_acc or 0.0)*hold_n)); global_low,_=wilson_interval(global_correct,hold_n)
            selection_local=local_selection_acc if local_selection_acc is not None else local_acc
            selection_global=global_holdout_acc
            selection_local_low=wilson_interval(int(round((selection_local or 0.0)*selection_n)),selection_n)[0] if selection_n else 0.0
            selection_global_low=wilson_interval(int(round((selection_global or 0.0)*selection_n)),selection_n)[0] if selection_n else 0.0
            local_eligible = (
                sample_n >= 200 and hold_n >= MIN_CHAMPION_HOLDOUT and selection_n >= 40 and
                local_acc >= 0.55 and local_low >= 0.50 and selection_local is not None and selection_global is not None and
                selection_local >= selection_global + 0.02 and selection_local_low >= selection_global_low
            )
            lgb_local_acc = float((lgb_rep or {}).get('holdoutAccuracy',0.0) or 0.0)
            lgb_hold_n = int((lgb_rep or {}).get('holdoutSamples',0) or 0)
            candidates=[('xgb-global',global_holdout_acc),('xgb-local',local_selection_acc if local_eligible else None),('lgb-global',lgb_global_same),('lgb-local',lgb_local_selection_acc if selection_n>=40 and lgb_hold_n>=MIN_CHAMPION_HOLDOUT and lgb_local_selection_acc is not None and lgb_local_selection_acc>=.55 and wilson_interval(int(round(lgb_local_selection_acc*selection_n)),selection_n)[0]>=.50 else None)]
            valid=[c for c in candidates if c[1] is not None]
            market_champion=max(valid,key=lambda z:z[1])[0] if valid else 'xgb-global'
            per_asset[asset] = {
                'trained': True, **rep,
                'globalHoldoutAccuracy': global_holdout_acc,
                'localAdvantage': advantage,
                'localEligible': bool(local_eligible),
                'champion': 'local' if local_eligible else 'global',
                'lightgbmHoldoutAccuracy': lgb_local_acc if lgb_model is not None else None,
                'lightgbmHoldoutSamples': lgb_hold_n,
                'lightgbmGlobalHoldoutAccuracy': lgb_global_same,
                'marketChampion': market_champion,
                'localWilsonLow': local_low,
                'globalWilsonLow': global_low,
                'championMinHoldout': MIN_CHAMPION_HOLDOUT,
                'selectionSamples': selection_n,
                'selectionCutoffTs': clean_cut,
                'xgbGlobalSelectionAccuracy': global_holdout_acc,
                'xgbLocalSelectionAccuracy': local_selection_acc,
                'lgbGlobalSelectionAccuracy': lgb_global_same,
                'lgbLocalSelectionAccuracy': lgb_local_selection_acc
            }
        else:
            per_asset[asset] = {'trained': False, **rep}

    global_model['assetModels'] = asset_models
    global_model['lightgbmGlobal'] = lgb_global
    global_model['lightgbmAssetModels'] = lgb_asset_models
    global_model['marketAware'] = True
    global_model['assetModelMinSamples'] = MIN_ASSET_MODEL_SAMPLES

    report = {
        **global_report,
        'rawSamplesReceived': raw_valid_count,
        'independentSamples': len(rows),
        'dedupedSamples': max(0, raw_valid_count-len(rows)),
        'assets': sorted(grouped.keys()),
        'featureCount': FEATURES,
        'trainerSchema': 'V235_CANONICAL_104_FEATURE',
        'targetHorizonMs': target,
        'modelType': 'xgboost-lightgbm-native-market-champion',
        'lightgbmAvailable': HAS_LIGHTGBM,
        'lightgbmGlobal': lgb_global_report,
        'marketAware': True,
        'assetModels': sorted(asset_models.keys()),
        'perAsset': per_asset
    }
    return {'ok': True, 'status': 'trained', 'model': global_model, 'report': report}


if __name__ == '__main__':
    try:
        msg = json.loads(sys.stdin.read())
        print(json.dumps(main(msg), separators=(',', ':')), flush=True)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}, separators=(',', ':')), flush=True)
