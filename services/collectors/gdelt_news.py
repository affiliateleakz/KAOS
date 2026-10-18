"""GDELT DOC public article discovery for explicit issuer/topic watchlists.

Neutral evidence only: the API's `seendate` is GDELT discovery time,
NOT a guaranteed publisher timestamp. No news sentiment or trading orders.
"""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen
from collector_common import read_json, submit, utc

ENDPOINT = 'https://api.gdeltproject.org/api/v2/doc/doc'
SYMBOL_RE = re.compile(r'^[A-Z][A-Z0-9.]{0,11}$')
QUERY_RE = re.compile(r'^[\w\s\-.,():"/$&|]+$', flags=re.UNICODE)


def validate_watchlist(raw):
    if not isinstance(raw, list) or len(raw) > 40:
        raise ValueError('news_watchlist must be an array of at most 40 explicit mappings')
    result, seen = [], set()
    for x in raw:
        if not isinstance(x, dict) or set(x) != {'symbol', 'query'}:
            raise ValueError('News watch item must have only symbol and query')
        symbol, query = x['symbol'], x['query']
        if not isinstance(symbol, str) or not SYMBOL_RE.fullmatch(symbol):
            raise ValueError('Invalid news symbol')
        if not isinstance(query, str) or not 3 <= len(query.strip()) <= 120 or not QUERY_RE.fullmatch(query):
            raise ValueError('Invalid GDELT query')
        if symbol in seen: raise ValueError('Duplicate news symbol')
        seen.add(symbol)
        result.append({'symbol': symbol, 'query': query.strip()})
    return result


def fetch_articles(query, *, timespan='24h', max_records=30, opener=urlopen):
    if not isinstance(query,str) or not 3 <= len(query.strip()) <= 120 or not QUERY_RE.fullmatch(query):
        raise ValueError('Invalid GDELT news query')
    if timespan not in {'1h','6h','12h','24h','48h','7d'}:
        raise ValueError('Unsupported timespan')
    if not 1 <= max_records <= 75:
        raise ValueError('Invalid article limit')
    url = ENDPOINT + '?' + urlencode({'query':query,'mode':'artlist','format':'json',
                                     'timespan':timespan,'sort':'datedesc','maxrecords':max_records})
    data = read_json(url, opener=opener)
    if not isinstance(data, dict) or not isinstance(data.get('articles'), list):
        raise ValueError('Unexpected GDELT DOC article response')
    return data['articles']


def parse_seen_at(raw):
    """GDELT 'seendate' represents GDELT first-seen timing, not article publish time."""
    if not isinstance(raw,str): raise ValueError('Missing GDELT first-seen timestamp')
    return datetime.strptime(raw, '%Y%m%dT%H%M%SZ' if raw.endswith('Z') else '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)


def observe_articles(symbol, query, articles, now=None, *, max_items=12):
    now=utc(now or datetime.now(timezone.utc))
    if not SYMBOL_RE.fullmatch(symbol): raise ValueError('Invalid symbol')
    if not isinstance(articles,list): raise ValueError('Articles must be a list')
    result, seen_urls = [], set()
    for article in articles:
        if not isinstance(article,dict): continue
        url=article.get('url')
        title=article.get('title')
        if not isinstance(url,str) or not url.startswith('https://') or len(url)>1800:
            continue
        if not isinstance(title,str) or not title.strip(): continue
        try:
            first_seen=parse_seen_at(article.get('seendate'))
        except (ValueError,TypeError):
            continue
        if first_seen>now or now-first_seen>timedelta(days=7): continue
        if url in seen_urls: continue
        seen_urls.add(url)
        event_id='gdelt:'+symbol+':'+hashlib.sha256(url.encode()).hexdigest()[:24]
        domain=str(article.get('domain') or 'source unknown')[:100]
        summary=(f'GDELT article match for configured topic {query!r}: '
                 f'{title.strip()[:330]} ({domain}). '
                 'First seen by GDELT, NOT verified publication timestamp; '
                 'coverage mention does not imply price direction or credibility.')
        result.append({'asset':symbol,'asset_class':'stock','source':'news',
                       'direction':'neutral','strength':0.25,'event_id':event_id,
                       'observed_at':now.isoformat(), 'published_at':first_seen.isoformat(),
                       'source_url':url,'summary':summary[:1200]})
        if len(result)>=max_items: break
    return result


def run(watchlist, *, now=None, opener=urlopen, pause_seconds=1.0):
    watchlist=validate_watchlist(watchlist)
    now=utc(now or datetime.now(timezone.utc))
    observations, issues=[], []
    for n, item in enumerate(watchlist):
        if n and pause_seconds: time.sleep(pause_seconds)
        try:
            articles=fetch_articles(item['query'],opener=opener)
            observations.extend(observe_articles(item['symbol'],item['query'],articles,now))
        except Exception as exc:
            issues.append({'provider':'gdelt','symbol':item['symbol'],'reason':str(exc)})
    return observations, issues


def main():
    p=argparse.ArgumentParser(description='KAOS neutral public news-discovery research adapter')
    p.add_argument('--config',default='market_universe.example.json')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    args=p.parse_args()
    doc=json.load(open(args.config,encoding='utf-8'))
    observations,issues=run(doc.get('news_watchlist',[]))
    result={'provider':'gdelt','observations_count':len(observations),'issues':issues,'mode':'research_only'}
    if args.dry_run: result['observations']=observations
    else: result['delivery']=submit(observations,args.api)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
