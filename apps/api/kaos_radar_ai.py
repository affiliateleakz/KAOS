"""KAOS-owned, local evidence model. Distinct from the short-expiry broker model.

No language-model API, downloads, orders, or heavy training dependencies. Text is
converted into explicit lexical features, not claimed to be language understanding.
Snapshots retain information availability times; labels use later closed candles.
"""
import asyncio
import math
import json
import re
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from db import db
from kaos_opportunity import utc

from radar_sentiment import analyzer, text_score, summarize

SCHEMA = 'kaos-radar-vader-mentions-v1'
HORIZON = 2700
FEATURES = ('return_1', 'return_4', 'return_20', 'trend', 'range_position',
            'volume_ratio', 'atr_fraction', 'news_tone', 'news_count',
            'social_tone', 'social_count', 'insider_balance',
            'government_balance', 'insider_count', 'government_count', 'whale_count', 'source_coverage',
            'reddit_mentions', 'x_mentions', 'mention_rank', 'reddit_available', 'x_available')

def evidence_features(evidence, symbol, kind, now):
    analyzer()
    rows = []
    seen = set()
    for row in evidence:
        if row.get('asset') != symbol or row.get('asset_class') != kind:
            continue
        try:
            published, observed = utc(row['published_at']), utc(row['observed_at'])
        except (KeyError, TypeError, ValueError):
            continue
        age_limit = timedelta(days=7) if row.get('source') in ('insider','politician','filing') else timedelta(hours=24)
        if not published <= observed <= now or now-published > age_limit:
            continue
        # Identical headlines/posts from multiple feeds count once.
        identity = re.sub(r'\W+', '', str(row.get('summary', '')).lower())
        reference=str(row.get('source_url','')).split('?')[0]
        if not identity or identity in seen or reference and reference in seen:
            continue
        seen.add(identity)
        if reference:seen.add(reference)
        rows.append(row)
    def group(source): return [r for r in rows if r.get('source') == source]
    def tone(source):
        values = [text_score(str(r.get('summary', ''))) for r in group(source)]
        return sum(values)/len(values) if values else 0.0
    def balance(source):
        # Unknown transfers/owners are never guessed to be buying/selling.
        values = [{'bullish':1, 'bearish':-1}.get(r.get('direction'), 0) for r in group(source)]
        return sum(values)/len(values) if values else 0.0
    values = [tone('news'), math.log1p(len(group('news'))), tone('social'),
              math.log1p(len(group('social'))), balance('insider'),
              balance('politician'), math.log1p(len(group('insider'))), math.log1p(len(group('politician'))), math.log1p(len(group('onchain'))),
              len({r.get('source') for r in rows})/13]
    return values, rows


def sigmoid(value):
    return 1/(1+math.exp(-max(-40, min(40, value))))


def probability(model, features):
    if model.get('schema') != SCHEMA or model.get('features') != list(FEATURES):
        raise ValueError('Incompatible Radar model')
    if len(features) != len(FEATURES) or not all(math.isfinite(x) for x in features):
        raise ValueError('Invalid features')
    for field in ('means','scales','weights'):
        values=model.get(field,[])
        if len(values)!=len(FEATURES) or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
            raise ValueError('Invalid model coefficients')
    if any(s<=0 for s in model['scales']) or not math.isfinite(model['bias']):raise ValueError('Invalid model scaling')
    x = [max(-8,min(8,(v-m)/s)) for v,m,s in zip(features, model['means'], model['scales'])]
    return sigmoid(model['bias']+sum(w*v for w,v in zip(model['weights'], x)))


def train(rows):
    """Chronological split, horizon purge, train-only normalization; no shuffling."""
    clean = sorted([r for r in rows if r.get('schema') == SCHEMA and r.get('label') in (0, 1)
                    and len(r.get('x', [])) == len(FEATURES)
                    and all(isinstance(v, (int, float)) and math.isfinite(v) for v in r['x'])], key=lambda r:r['asof'])
    # All assets share timestamps: purge the split globally, not per ticker.
    if len(clean) < 120:
        return {'state':'collecting', 'samples':len(clean), 'required_samples':120}
    cutoff = clean[int(len(clean)*.75)]['asof']
    fitting = [r for r in clean if r['target_at'] < cutoff]
    held = [r for r in clean if r['asof'] >= cutoff]
    if len(fitting) < 80 or len(held) < 30 or min(sum(r['label']==y for r in fitting) for y in (0,1)) < 15:
        return {'state':'collecting', 'samples':len(clean), 'reason':'Need more purged training data and both directions.'}
    means = [sum(r['x'][i] for r in fitting)/len(fitting) for i in range(len(FEATURES))]
    scales = [max(1e-6, math.sqrt(sum((r['x'][i]-means[i])**2 for r in fitting)/len(fitting))) for i in range(len(FEATURES))]
    matrix = [[max(-8, min(8, (v-m)/s)) for v,m,s in zip(r['x'],means,scales)] for r in fitting]
    weights = [0.0]*len(FEATURES)
    bias = 0.0
    for _ in range(100):
        grad = [0.0]*len(weights)
        gb = 0.0
        for row,x in zip(fitting,matrix):
            error = sigmoid(bias+sum(w*v for w,v in zip(weights,x)))-row['label']
            gb += error
            for i,v in enumerate(x): grad[i] += error*v
        bias -= .05*gb/len(fitting)
        weights = [w-.05*(g/len(fitting)+.02*w) for w,g in zip(weights,grad)]
    model = {'schema':SCHEMA, 'features':list(FEATURES), 'means':means, 'scales':scales,
             'weights':weights, 'bias':bias, 'trained_through':max(r['target_at'] for r in clean)}
    predictions = [probability(model,r['x']) for r in held]
    recalls = [sum((p>=.5)==r['label'] for p,r in zip(predictions,held) if r['label']==y)/max(1,sum(r['label']==y for r in held)) for y in (0,1)]
    balanced = sum(recalls)/2
    actionable = [(p,r) for p,r in zip(predictions,held) if p>=.6 or p<=.4]
    accuracy = sum((p>=.5)==r['label'] for p,r in actionable)/max(1,len(actionable))
    # A candidate is not deployed by training. Independent future validation is
    # retained for review; historical directional accuracy is not profitability.
    metrics = {'train_samples':len(fitting), 'holdout_samples':len(held),
               'balanced_accuracy':balanced, 'signal_samples':len(actionable),
               'signal_accuracy':accuracy, 'purged':len(clean)-len(fitting)-len(held),
               'holdout_start':cutoff, 'holdout_end':clean[-1]['target_at']}
    passed = balanced >= .55 and len(actionable)>=15 and accuracy>=.6 and all(sum(r['label']==y for r in held)>=10 for y in (0,1))
    return {'state':'candidate' if passed else 'validation_failed', 'metrics':metrics, 'bundle':model}


async def assessment(asset, market, evidence, now=None, discovery=None):
    now = now or datetime.now(timezone.utc)
    symbol, kind = asset['symbol'], asset['asset_class']
    discovery_values=[0.0]*5
    extras=[]
    if discovery and kind in ('stock','etf'):
        try:
            collected=utc(discovery['completed_at'])
            if not timedelta(0)<=now-collected<=timedelta(minutes=15):raise ValueError('Stale discovery')
            available={r['provider']:float(r.get('state')=='collected') for r in discovery.get('source_status',[])}
            discovery_values[-2:]=[available.get('reddit',0.0),available.get('x',0.0)]
            for index,row in enumerate(discovery.get('rankings',[])):
                if row['symbol']!=symbol:continue
                discovery_values=[math.log1p(row['reddit']),math.log1p(row['x']),1/(index+1),available.get('reddit',0.0),available.get('x',0.0)]
                for post in row.get('posts',[]):
                    extras.append({'asset':symbol,'asset_class':kind,'source':'social',
                        'id':sha256(post['source_url'].encode()).hexdigest()[:20],
                        'published_at':post['published_at'],'observed_at':collected.isoformat(),
                        'summary':post['text'],'source_url':post['source_url']})
        except (ValueError,KeyError,TypeError):
            discovery_values=[0.0]*5;extras=[]
    try:
        context, cited = evidence_features(evidence+extras,symbol,kind,now)
    except ImportError:
        return {'symbol':symbol,'asset_class':kind,'direction':'WAIT','priority':'low',
                'model_state':'dependency_missing','explanation':'Install the updated backend requirements to enable local sentiment.',
                'evidence_ids':[],'limitations':['Local sentiment is unavailable; no AI signal was generated.']}
    result = {'symbol':symbol, 'asset_class':kind, 'direction':'WAIT', 'priority':'low',
              'evidence_ids':[r['id'] for r in cited if r.get('id')][:8],
              'supporting_sources':[{k:r.get(k) for k in ('id','source','summary','source_url','published_at')} for r in cited[:8]],
              'market_source':market.get('source'), 'reference_price':market.get('price'),
              'issued_at':now.isoformat(), 'expires_at':(now+timedelta(minutes=15)).isoformat(),
              'limitations':['English lexical sentiment can misread financial language, sarcasm, multilingual text or complex events.',
                             'Labels compare future closes with the last observed close, not broker execution prices; fees and slippage are not modeled.'],
              'explanation':'Collecting evidence and future outcomes for the KAOS Radar model.', 'model_state':'collecting'}
    result['sentiment'] = summarize(cited)
    result['evidence_count'] = len(cited)
    technical = market.get('feature_vector')
    if not isinstance(technical,list) or len(technical)!=7 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in technical):
        technical=None
    # Public, aggregate sentiment history: one point per asset/five-minute bucket.
    await db.kaos_radar_sentiment.update_one(
        {'_id':f'{kind}:{symbol}:{int(now.timestamp())//300}'},
        {'$set':{'symbol':symbol,'asset_class':kind,'observed_at':now.isoformat(),
                 'sentiment':result['sentiment'],'expires_at':now+timedelta(days=7),'return_1':(technical or [None]*7)[0],
                 'return_4':(technical or [None]*7)[1],'volume_ratio':(technical or [None]*7)[5]}},upsert=True)
    if not technical or len(technical)!=7 or not market.get('source_time'):
        return {**result, 'model_state':'market_unavailable', 'explanation':market.get('reason','Fresh market candles are required.')}
    try:
        source_time = utc(market['source_time'])
    except (ValueError,TypeError):
        return {**result,'model_state':'invalid_features','explanation':'Invalid market timestamp; no signal generated.'}
    if not timedelta(0) <= now-source_time <= timedelta(minutes=20):
        return {**result,'model_state':'stale','explanation':'Fresh market candles are required.'}
    vector = technical+context+discovery_values
    if not all(math.isfinite(v) for v in vector):
        return {**result, 'model_state':'invalid_features','explanation':'Invalid input; no signal generated.'}
    result['feature_values'] = dict(zip(FEATURES,vector))
    result['source_time'] = market['source_time']
    group = 'crypto' if kind == 'crypto' else 'stock'
    # Actual later closed-candle prices label prior snapshots, never provider text
    # or a guessed trade outcome. Session gaps cannot become 45-minute labels.
    history = {int(t):p for t,p in market.get('closed_history', [])}
    pending = await db.kaos_radar_samples.find({'group':group,'symbol':symbol,'label':{'$exists':False},
                                               'target_at':{'$lte':source_time.timestamp()},'source_at':{'$gte':min(history) if history else source_time.timestamp()}}, {'_id':1,'target_at':1,'source_at':1,'price':1}).limit(100).to_list(100)
    for row in pending:
        target = int(row['target_at'])
        if target not in history or any(t not in history for t in range(int(row['source_at']),target+1,900)):
            continue
        move = history[target]/row['price']-1
        # Flat moves under ten basis points do not become directional labels.
        await db.kaos_radar_samples.update_one({'_id':row['_id'],'label':{'$exists':False}},
            {'$set':{'label':int(move>0) if abs(move)>=.001 else None,'forward_return':move}})
    key = sha256(f'{SCHEMA}:{kind}:{symbol}:{source_time.timestamp()}'.encode()).hexdigest()
    await db.kaos_radar_samples.update_one({'_id':key},{'$setOnInsert':{
        'schema':SCHEMA,'group':group,'symbol':symbol,'x':vector,'asof':now.timestamp(),
        'source_at':source_time.timestamp(), 'target_at':(math.floor(now.timestamp()/900)+1)*900+HORIZON,
        'price':market['price'],'expires_at':now+timedelta(days=90)}},upsert=True)
    model = await db.kaos_radar_models.find_one({'_id':group,'state':'active'})
    if not model:
        return result
    bundle = model['bundle']
    if not 0 <= now.timestamp()-model.get('activated_at',0) <= 30*86400 or not 0 < now.timestamp()-bundle.get('trained_through',now.timestamp()) <= 30*86400:
        return {**result,'model_state':'expired','explanation':'Model needs fresh validation before it can issue signals.'}
    try:
        p = probability(bundle, vector)
    except (ValueError, TypeError, KeyError, OverflowError):
        return {**result,'model_state':'incompatible','explanation':'Model schema does not match the evidence features.'}
    normalized = [max(-8,min(8,(v-m)/scale)) for v,m,scale in zip(vector,bundle['means'],bundle['scales'])]
    contributions = sorted([{'feature':name,'contribution':round(w*v,4)} for name,w,v in zip(FEATURES,bundle['weights'],normalized)], key=lambda item:abs(item['contribution']),reverse=True)[:5]
    direction = 'BUY' if p>=.6 else 'SELL' if p<=.4 else 'WAIT'
    return {**result,'model_state':'active','direction':direction,'priority':'medium' if direction!='WAIT' else 'low',
            'model_score_up':round(p,4), 'model_version':model.get('version'),
            'explanation':f'KAOS local evidence model: {direction}. Uses candle movement/volume and available news, social and disclosure features; missing feeds remain gaps.',
            'horizon':'45–60 minutes from collection', 'factors':contributions, 'feature_values':dict(zip(FEATURES,vector))}


_indexes_ready = False


async def ensure_indexes():
    global _indexes_ready
    if _indexes_ready:return
    await db.kaos_radar_sentiment.create_index([('symbol',1),('asset_class',1),('observed_at',-1)])
    await db.kaos_radar_sentiment.create_index('expires_at',expireAfterSeconds=0)
    await db.kaos_radar_samples.create_index([('group',1),('symbol',1),('target_at',1)])
    await db.kaos_radar_samples.create_index('expires_at',expireAfterSeconds=0)
    _indexes_ready=True


async def analyze(assets,evidence,source_status,settings=None):
    await ensure_indexes()
    # Import here to avoid router/model import cycles.
    from radar_signals import market
    from types import SimpleNamespace
    markets = await asyncio.gather(*(market(SimpleNamespace(**asset)) for asset in assets))
    stamp=datetime.now(timezone.utc)
    query={'checked':{'$gte':stamp.timestamp()-900}}
    if settings is not None:
        query['_id']=sha256(json.dumps({p:settings[p] for p in ('reddit','x')},sort_keys=True).encode()).hexdigest()
    cached=await db.kaos_social_mentions.find_one(query,sort=[('checked',-1)])
    discovery=cached.get('report') if cached else None
    reports = await asyncio.gather(*(assessment(asset,quote,evidence,stamp,discovery) for asset,quote in zip(assets,markets)))
    gaps = sorted({f"{row.get('provider')}: {row.get('state')}" for row in source_status
                   if row.get('state') not in ('collected','no_matches','not_applicable')})
    if not discovery:gaps.append('Market-wide discussion discovery has not been scanned recently; per-ticker social evidence is used when available.')
    return {'state':'complete','model':'KAOS Radar · local evidence model',
            'report':{'summary':'KAOS combines available evidence locally. Untrained, stale or unvalidated models return WAIT. No OpenAI service is used.',
                      'assets':reports,'coverage_gaps':gaps},
            'observations_reviewed':sum(row.get('evidence_count',0) for row in reports),
            'research_only':True,'trade_execution_enabled':False}
