"""Owner-configured Alpha Vantage news; shared cache and conservative free quota."""
from datetime import datetime, timezone
from hashlib import sha256
from pymongo.errors import DuplicateKeyError
from db import db
from radar_sources import Sources, SourceIssue
import radar_settings


async def news():
    cfg=await radar_settings.settings('alphavantage')
    if not cfg.get('enabled',True) or not cfg.get('api_key') or cfg.get('configuration_error'):
        raise SourceIssue('setup_required','Add the Alpha Vantage key once in Admin → Radar Sources.')
    fingerprint=sha256(cfg['api_key'].encode()).hexdigest()
    now=datetime.now(timezone.utc);stamp=now.timestamp()
    cached=await db.kaos_alpha_cache.find_one({'_id':fingerprint})
    if cached and stamp-cached.get('checked',0)<3600:
        if cached.get('error'):raise SourceIssue(cached['error']['state'],cached['error']['message'])
        return cached['feed']
    try:
        await db.kaos_alpha_locks.update_one({'_id':fingerprint,'until':{'$lt':stamp}}, {'$set':{'until':stamp+20}},upsert=True)
    except DuplicateKeyError:
        raise SourceIssue('collecting','News is refreshing. Try again shortly.')
    source=Sources({})
    try:
        budget=fingerprint+':'+now.strftime('%Y-%m-%d')
        try:
            await db.kaos_alpha_usage.update_one({'_id':budget,'count':{'$lt':20}}, {'$inc':{'count':1}},upsert=True)
        except DuplicateKeyError:
            raise SourceIssue('rate_limited','KAOS’s daily news allowance is used. Saved headlines remain available.')
        data=await source.request('GET','https://www.alphavantage.co/query',params={'function':'NEWS_SENTIMENT','limit':50,'sort':'LATEST','apikey':cfg['api_key']})
        if not isinstance(data,dict) or not isinstance(data.get('feed'),list):
            raise SourceIssue('unavailable','Alpha Vantage news is unavailable or this key has reached its plan limit.')
        feed=data['feed'][:50]
        await db.kaos_alpha_cache.update_one({'_id':fingerprint},{'$set':{'checked':stamp,'feed':feed},'$unset':{'error':''}},upsert=True)
        return feed
    except SourceIssue as error:
        await db.kaos_alpha_cache.update_one({'_id':fingerprint},{'$set':{'checked':stamp,'error':{'state':error.state,'message':error.message}}},upsert=True)
        raise
    finally:
        await source.close()
        await db.kaos_alpha_locks.update_one({'_id':fingerprint},{'$set':{'until':0}})
