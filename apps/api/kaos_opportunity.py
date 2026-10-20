"""KAOS 3.0 research-only opportunity fusion. No orders, no predictive claims.

Scores rank *research attention* only. Repeating one source cannot fabricate
independent agreement. Neutral evidence never supplies directional votes.
"""
from datetime import datetime, timezone
from math import exp, isfinite

SUPPORTED = {'stock','etf','option','crypto','dex','forex','future'}
SOURCES = {'technical','news','filing','social','insider','institutional','politician','onchain','options_flow','liquidity','macro','dark_pool','short_interest'}


def utc(value):
    if isinstance(value,str): value=datetime.fromisoformat(value.replace('Z','+00:00'))
    if not isinstance(value,datetime) or value.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return value.astimezone(timezone.utc)


def evaluate(asset, observations, now=None):
    now=utc(now or datetime.now(timezone.utc))
    seen=set(); details=[]; votes={}; neutral=set()
    for o in observations:
        if not isinstance(o,dict):continue
        source=o.get('source'); direction=o.get('direction')
        if source not in SOURCES or direction not in ('bullish','bearish','neutral'):continue
        try:
            at=utc(o['observed_at']); published=utc(o['published_at'])
            age=(now-min(at,published)).total_seconds()/3600
            strength=float(o.get('strength',0))
        except (KeyError,ValueError,TypeError,OverflowError):continue
        if at>now or published>at or age<0 or age>168 or not isfinite(strength):continue
        event_id=o.get('event_id') or o.get('id')
        # A missing event identity must not become one shared synthetic vote.
        if not isinstance(event_id,str) or not event_id.strip():continue
        key=(source,event_id)
        if key in seen:continue
        seen.add(key)
        weight=max(0.,min(1.,strength))*exp(-age/24)
        details.append({'source':source,'direction':direction,'observed_at':at.isoformat(),
                        'published_at':published.isoformat(),'source_url':o.get('source_url'),
                        'weight':round(weight,4),'summary':str(o.get('summary',''))[:1200]})
        if direction=='neutral':neutral.add(source)
        else:
            # Highest-weight observation per (category, direction), rather
            # than unlimited counting of many articles or reposts.
            vote_key=(source,direction)
            votes[vote_key]=max(votes.get(vote_key,0),weight)
    support={direction:sum(v for (s,d),v in votes.items() if d==direction)
             for direction in ('bullish','bearish')}
    directionals={direction:{s for (s,d),v in votes.items() if d==direction and v>0}
                  for direction in ('bullish','bearish')}
    bullish,bearish=support['bullish'],support['bearish']
    if bullish>0 and bearish>0 and min(bullish,bearish)>=.25*max(bullish,bearish):
        bias='mixed'
    elif bullish>bearish: bias='bullish'
    elif bearish>bullish: bias='bearish'
    else: bias='mixed'
    agreeing=len(directionals.get(bias,set()))
    opposing=len(directionals['bearish' if bias=='bullish' else 'bullish']) if bias!='mixed' else 0
    diversity=len({d['source'] for d in details})
    context=min(3,len(neutral))*3
    # Priority score (not likelihood of winning): capping categories stops
    # frequent polls of one provider from overwhelming independent evidence.
    score=round(min(100,max(0,(bullish+bearish)*22 +
                 len(directionals['bullish']|directionals['bearish'])*5 + context -
                 min(bullish,bearish)*18)),1)
    if not bullish and not bearish:status='context_only'
    elif bias=='mixed': status='conflicting_evidence'
    elif agreeing>=2 and opposing==0:status='research_candidate'
    else:status='insufficient_confirmation'
    details.sort(key=lambda d:d['weight'],reverse=True)
    return {'asset':asset,'score':score,'bias':bias,'independent_sources':diversity,
            'confirming_directional_sources':agreeing,'opposing_directional_sources':opposing,
            'status':status,'evidence':details[:30],
            'evidence_truncated':len(details)>30,
            'score_type':'heuristic_research_priority_not_win_probability',
            'trade_recommendation':False}
