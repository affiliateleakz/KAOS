"""Simple news feed, shared with KAOS evidence collection."""
from datetime import datetime,timezone,timedelta
from fastapi import Depends
from routes_radar import router
from routes_opportunity import member
from radar_sources import SourceIssue
from db import db


def normalize(items):
    now=datetime.now(timezone.utc);rows=[]
    for item in items:
        try:
            published=datetime.strptime(item['time_published'],'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
            url=item['url']
            if not isinstance(url,str) or not url.startswith('https://') or not now-timedelta(days=7)<=published<=now:continue
            rows.append({'title':str(item.get('title',''))[:300],'summary':str(item.get('summary',''))[:1200],
                'source':str(item.get('source','Alpha Vantage'))[:120],'source_url':url[:2000],
                'published_at':published.isoformat(),'tickers':[r['ticker'] for r in item.get('ticker_sentiment',[]) if isinstance(r,dict) and isinstance(r.get('ticker'),str)][:20]})
        except (KeyError,ValueError,TypeError):continue
    return rows


@router.post('/news/feed')
async def feed(user=Depends(member)):
    import alpha_vantage
    try:
        rows=normalize(await alpha_vantage.news())
        return {'articles':rows,'state':'complete','source':'Alpha Vantage','message':None}
    except SourceIssue as error:
        cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
        saved=await db.kaos_intelligence.find({'source':'news','published_at':{'$gte':cutoff}}, {'_id':0}).sort('published_at',-1).limit(30).to_list(30)
        rows=list({r['source_url']:{'title':r.get('summary',''),'summary':'','source':r.get('provider','Saved news'),
                                  'source_url':r['source_url'],'published_at':r['published_at'],'tickers':[r['asset']]} for r in saved if isinstance(r.get('source_url'),str) and r['source_url'].startswith('https://')}.values())
        return {'articles':rows,'state':error.state,'source':'Saved news','message':error.message}
