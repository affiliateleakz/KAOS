"""One explainable asset score for both research and discovery. No probability claims."""
import math
import re
from datetime import datetime,timezone
from kaos_opportunity import utc
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

EXTRA_CHANNELS=('filing','institutional','onchain','options_flow','liquidity','macro','dark_pool','short_interest')
CHANNEL_NAMES={'news':'News','social':'Social post text','insider':'Insider disclosures','politician':'Government disclosures',
 'filing':'Company filings','institutional':'Institutional activity','onchain':'Whale/on-chain activity',
 'options_flow':'Options activity','liquidity':'Liquidity','macro':'Macro events','dark_pool':'Dark-pool activity','short_interest':'Short interest'}


def channels(rows,now):
    result={name:{'source':name,'label':label,'count':0,'bullish':0.,'bearish':0.,'max_strength':0.,'balance':0.} for name,label in CHANNEL_NAMES.items()}
    seen=set()
    for row in rows:
        source=row.get('source')
        if source not in result:continue
        try:
            published=utc(row['published_at']);observed=utc(row['observed_at'])
            age=(now-published).total_seconds()/3600
            if not published<=observed<=now or age>(168 if source in ('filing','insider','politician') else 24):continue
            identity=(source,str(row.get('event_id') or row.get('id') or row.get('summary')))
            if identity in seen:continue
            seen.add(identity)
            strength=float(row.get('strength',0))
            if not math.isfinite(strength):continue
            strength=max(0,min(1,strength))
        except (TypeError,ValueError,KeyError):continue
        item=result[source];item['count']+=1;item['max_strength']=max(item['max_strength'],strength)
        direction=row.get('direction')
        if direction in ('bullish','bearish'):
            item[direction]=max(item[direction],strength*math.exp(-age/24))
    for item in result.values():item['balance']=item['bullish']-item['bearish']
    return result


def extra_features(channel_data):
    return [value for name in EXTRA_CHANNELS for value in (
        channel_data[name]['balance'],math.log1p(channel_data[name]['count']),channel_data[name]['max_strength'])]


def attention(asset,trending):
    if asset['asset_class'] not in ('stock','etf'):
        return {'state':'not_applicable','provider':'ApeWisdom','mentions':None,'fetched_at':None}
    row=next((r for r in (trending or {}).get('rankings',[]) if r['symbol']==asset['symbol']),None)
    state='available' if row else 'not_ranked' if (trending or {}).get('state')=='complete' else 'unavailable'
    if (trending or {}).get('stale'):state='stale'
    return {**(row or {}),'mentions':row.get('mentions') if row else None,'state':state,
        'provider':'ApeWisdom','fetched_at':(trending or {}).get('fetched_at'),
        'meaning':'Provider stock mentions, not the number of news articles or a sentiment score.'}


def score(asset,quote,ai,now=None):
    now=now or datetime.now(timezone.utc)
    channel_data=ai.get('evidence_channels') or channels([],now)
    interest=ai.get('attention') or {'state':'unavailable'}
    coverage=[{'source':k,'label':v['label'],'state':'available' if v['count'] else 'missing','items':v['count']} for k,v in channel_data.items()]
    if asset['asset_class'] in ('stock','etf') and not channel_data['onchain']['count']:
        next(c for c in coverage if c['source']=='onchain')['state']='not_applicable'
    coverage.extend([{'source':'attention','label':'Reddit mention trends','state':interest['state'],'items':interest.get('mentions')},
                     {'source':'model','label':'Validated KAOS model','state':'available' if ai.get('model_state')=='active' else 'missing','items':None}])
    base={'score':None,'direction':'WAIT','eligible':False,'components':{},'coverage':coverage,
          'score_type':'Evidence setup quality, not win probability','version':'kaos-asset-score-v2'}
    x=quote.get('feature_vector')
    try:
        if not x or len(x)!=7 or not all(math.isfinite(v) for v in x):raise ValueError('No candle features')
        stamp=utc(quote['source_time']);price=float(quote['price'])
        if not 0<=(now-stamp).total_seconds()<1200 or not math.isfinite(price) or price<=0:raise ValueError('Stale price')
        r1,r4,_,trend,position,volume,atr=x
        if not 0<atr<=.1:raise ValueError('Invalid volatility')
    except (ValueError,TypeError,KeyError):
        base['coverage'].insert(0,{'source':'technical','label':'Price & volume','state':'missing','items':None})
        applicable=[c for c in coverage if c['state']!='not_applicable']
        return {**base,'coverage_percent':round(100*sum(c['state']=='available' for c in applicable)/len(applicable)),
                'reason':'Fresh, valid market candles are required to score this instrument.'}
    base['coverage'].insert(0,{'source':'technical','label':'Price & volume','state':'available','items':None})
    aligned=trend>0 and r4>0 and r1>0 or trend<0 and r4<0 and r1<0
    sign=1 if trend>=0 else -1
    direction='BUY' if sign>0 else 'SELL'
    overextended=abs(r4)/atr>3.5
    points={'trend':round(25*min(1,abs(trend)/atr/.75),2),'momentum':20 if aligned else 0,
        'range':15 if (position>1 if sign>0 else position<0) else 8 if (position>.6 if sign>0 else position<.4) else 0,
        'risk':0 if overextended else 10 if abs(r4)/atr<=2 else 5,
        'news':0,'social_text':0,'attention':0,'disclosures':0,'large_holder_activity':0,'derivatives_macro_liquidity':0,'ai_confirmation':0}
    if asset['asset_class']!='forex':points['volume']=10 if volume>=1.2 else 5 if volume>=.8 else 0
    tone=ai.get('sentiment',{}).get('sources',{}).get('news',{})
    if tone.get('samples') and tone.get('score') is not None:
        points['news']=4 if sign*tone['score']>=.05 else -4 if sign*tone['score']<=-.05 else 0
    social=ai.get('sentiment',{}).get('sources',{}).get('social',{})
    if social.get('samples') and social.get('score') is not None:
        points['social_text']=1 if sign*social['score']>=.05 else -1 if sign*social['score']<=-.05 else 0
    if interest.get('state')=='available':
        previous=interest.get('previous_mentions');current=interest.get('mentions')
        if previous is not None and current is not None and current>previous:
            points['attention']=round(3*min(1,(current-previous)/max(1,previous)),2)
    def contribution(weights):return round(sum(weight*sign*channel_data[name]['balance'] for name,weight in weights.items()),2)
    points['disclosures']=contribution({'insider':1.5,'politician':1,'filing':.5})
    points['large_holder_activity']=contribution({'institutional':1.5,'onchain':1.5})
    points['derivatives_macro_liquidity']=contribution({'options_flow':.5,'liquidity':.5,'macro':.5,'dark_pool':.25,'short_interest':.25})
    model_active=ai.get('model_state')=='active'
    confirmed=model_active and ai.get('direction')==direction
    opposed=model_active and ai.get('direction') in ('BUY','SELL') and ai['direction']!=direction
    points['ai_confirmation']=4 if confirmed else -4 if opposed else 0
    denominator=90 if asset['asset_class']=='forex' else 100
    value=round(max(0,min(100,100*sum(points.values())/denominator)))
    applicable=[c for c in base['coverage'] if c['state']!='not_applicable']
    coverage_percent=round(100*sum(c['state']=='available' for c in applicable)/len(applicable))
    ready=aligned and not overextended and not opposed
    return {**base,'score':value,'direction':direction if ready else 'WAIT','eligible':ready,
        'components':points,'ai_confirmed':confirmed,'coverage_percent':coverage_percent,
        'context_level':'Broad evidence' if coverage_percent>=60 else 'Limited evidence',
        'reason':'Market trend and momentum agree; all available evidence is included.' if ready else
                 'Validated AI disagrees with the technical direction.' if opposed else
                 'Price is overextended relative to recent volatility.' if overextended else 'Trend and short-term momentum do not agree.'}


def reported_transactions(rows):
    counts=[0,0,0,0]
    for row in rows:
        event=str(row.get('event_id',''))
        if row.get('source')=='insider' and event.startswith('sec-form4-txn:'):
            code=event.rsplit(':',1)[-1]
            if code in ('P','S'):counts[0 if code=='P' else 1]+=1
        if row.get('source')=='politician' and row.get('provider')=='government':
            match=re.search(r'; reported (purchase|sale)(?: \(.*?\))? of ',row.get('summary',''),re.I)
            if match:counts[2 if match[1].lower()=='purchase' else 3]+=1
    return [math.log1p(value) for value in counts]


def canonical_url(value):
    """Discard tracking parameters, not article IDs carried in query strings."""
    try:
        parsed=urlsplit(str(value))
        query=[(key,val) for key,val in parse_qsl(parsed.query,keep_blank_values=True)
               if not key.lower().startswith('utm_') and key.lower() not in ('fbclid','gclid')]
        return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),''))
    except ValueError:return str(value)
