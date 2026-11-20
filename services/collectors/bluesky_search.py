"""Research-only public Bluesky cashtag sampling. No sentiment or trading orders.

Uses public AppView searchPosts GET, when available unauthenticated. This is a
bounded *search result sample*, not a complete platform stream or full count.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote
from urllib.request import urlopen
import re
import time
from collector_common import read_json, utc
from bluesky_social import CASHTAG, validate_cashtags

BASE = 'https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts'
URI = re.compile(r'^at://[^/]+/app\.bsky\.feed\.post/[a-zA-Z0-9]+$')


def fetch_search(symbol, *, opener=urlopen):
    symbol = validate_cashtags([symbol])[0]
    url = BASE + '?' + urlencode({'q': '$' + symbol, 'sort': 'latest', 'limit': 100})
    data = read_json(url, opener=opener, timeout=20)
    if not isinstance(data, dict) or not isinstance(data.get('posts'), list):
        raise ValueError('Bluesky search response missing posts')
    return data['posts'][:100]


def summarize_search(symbol, posts, *, now=None):
    symbol = validate_cashtags([symbol])[0]
    now = utc(now or datetime.now(timezone.utc))
    if not isinstance(posts, list): raise ValueError('Expected post list')
    dedup = {}
    for post in posts[:100]:
        if not isinstance(post, dict): continue
        record = post.get('record') or {}
        author = post.get('author') or {}
        uri = post.get('uri')
        if not isinstance(record, dict) or not isinstance(author, dict) or not isinstance(uri, str): continue
        if not URI.fullmatch(uri): continue
        body = record.get('text')
        if not isinstance(body, str) or symbol not in {t.upper() for t in CASHTAG.findall(body)}: continue
        try: ts = utc(post.get('indexedAt') or record.get('createdAt'))
        except (ValueError, TypeError, AttributeError): continue
        if not timedelta(0) <= now-ts <= timedelta(hours=2): continue
        author_id = author.get('did') or author.get('handle')
        if not isinstance(author_id, str) or not author_id: continue
        # Search can return duplicates; one record per immutable post URI.
        handle = author.get('handle') or uri.split('/')[2]
        if not isinstance(handle, str) or not re.fullmatch(r'[A-Za-z0-9.:-]{3,255}', handle): continue
        href = 'https://bsky.app/profile/' + quote(handle, safe='.-:') + '/post/' + uri.rsplit('/',1)[-1]
        dedup[uri] = (author_id, ts, href)
    current = [p for p in dedup.values() if now-p[1] <= timedelta(hours=1)]
    earlier = [p for p in dedup.values() if timedelta(hours=1) < now-p[1] <= timedelta(hours=2)]
    if not current: return None
    distinct_current = len({p[0] for p in current})
    distinct_prior = len({p[0] for p in earlier})
    latest = max(current, key=lambda p:p[1])
    # Do NOT call this market-wide velocity: search returns at most 100 results.
    summary = (
        f'Bluesky public search sample ${symbol}: {len(current)} matched posts / '
        f'{distinct_current} distinct authors in last 60 min; '
        f'{len(earlier)} posts / {distinct_prior} authors in preceding 60 min. '
        'Up to 100 latest search results inspected; coverage can truncate earlier posts. '
        'Not platform-wide sentiment or verified momentum; no trade direction inferred.'
    )
    return {
        'asset':symbol,'asset_class':'stock','source':'social','direction':'neutral',
        'strength':round(min(.50, .08 + .015*distinct_current),4),
        'event_id':f'bsky-search:{symbol}:{now.strftime("%Y%m%d%H")}',
        'observed_at':now.isoformat(),'published_at':latest[1].isoformat(),
        'source_url':latest[2],'summary':summary[:1200],
        'sample_metrics': {
            'provider': 'bluesky_search', 'sampled_posts': len(current),
            'sampled_unique_authors': distinct_current,
            'previous_hour_posts': len(earlier),
            'previous_hour_unique_authors': distinct_prior,
            'search_results_inspected': min(len(posts), 100),
            'search_limit': 100,
            'coverage': 'bounded_search_sample_not_platform_total',
        },
    }


def run(symbols, *, now=None, opener=urlopen, pause_seconds=1.5):
    symbols = validate_cashtags(symbols)
    if len(symbols)>20: raise ValueError('Public search supports at most 20 symbols per run')
    now=utc(now or datetime.now(timezone.utc))
    out=[];errors=[]
    for i,symbol in enumerate(symbols):
        if i and pause_seconds: time.sleep(pause_seconds)
        try:
            item=summarize_search(symbol,fetch_search(symbol,opener=opener),now=now)
            if item: out.append(item)
        except Exception as e:
            errors.append({'provider':'bluesky_search','symbol':symbol,'reason':type(e).__name__})
    return out,errors
