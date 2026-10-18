"""Free public Bluesky monitored-account social attention, research only.

NOT a comprehensive social firehose, sentiment classifier or short-squeeze signal.
Uses author-feed public reads; does NOT depend on full-text search which may need auth.
"""
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, quote
from urllib.request import urlopen
from collector_common import read_json, utc

BASE = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed'
HANDLE = re.compile(r'^(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$')
SYMBOL = re.compile(r'^[A-Z][A-Z0-9]{0,7}$')
CASHTAG = re.compile(r'(?<![a-zA-Z0-9])\$([A-Z][A-Z0-9]{0,7})(?![a-zA-Z0-9])', re.I)


def validate_social_accounts(raw):
    if not isinstance(raw, list) or len(raw) > 30:
        raise ValueError('social_accounts must contain at most 30 public Bluesky handles')
    result = []
    for name in raw:
        if not isinstance(name, str) or not HANDLE.fullmatch(name) or len(name) > 253:
            raise ValueError('Invalid Bluesky account handle')
        handle = name.lower()
        if handle not in result: result.append(handle)
    return result


def validate_cashtags(raw):
    if not isinstance(raw, list) or len(raw) > 120:
        raise ValueError('social_cashtags must contain at most 120 symbols')
    result = []
    for ticker in raw:
        if not isinstance(ticker, str) or not SYMBOL.fullmatch(ticker):
            raise ValueError('Cashtags must be uppercase symbols without dollar signs')
        if ticker not in result: result.append(ticker)
    return result


def fetch_feed(handle, *, opener=urlopen):
    validate_social_accounts([handle])
    url = BASE + '?' + urlencode({'actor': handle, 'filter': 'posts_no_replies', 'limit': 100})
    data = read_json(url, opener=opener, timeout=20)
    if not isinstance(data, dict) or not isinstance(data.get('feed'), list):
        raise ValueError('Bluesky feed response shape unexpected')
    return data['feed'][:100]


def _url(handle, uri):
    if not isinstance(uri, str) or not re.fullmatch(r'at://[^/]+/app\.bsky\.feed\.post/[A-Za-z0-9]+', uri):
        return None
    return 'https://bsky.app/profile/' + quote(handle, safe='.-') + '/post/' + uri.rsplit('/', 1)[-1]


def observe_accounts(feed_map, symbols, now=None):
    now = utc(now or datetime.now(timezone.utc))
    symbols = set(validate_cashtags(symbols))
    grouped = defaultdict(dict)
    for handle, feed in feed_map.items():
        if handle not in validate_social_accounts([handle]): continue
        if not isinstance(feed, list): continue
        for item in feed[:100]:
            if not isinstance(item, dict) or item.get('reason'):
                continue  # no repost amplification
            post = item.get('post') or {}
            rec = post.get('record') or {}
            author = post.get('author') or {}
            text = rec.get('text')
            uri = post.get('uri')
            href = _url(author.get('handle', handle), uri)
            if not isinstance(text, str) or not href: continue
            at = post.get('indexedAt') or rec.get('createdAt')
            try: published = utc(at)
            except (ValueError, TypeError, AttributeError): continue
            if not timedelta(seconds=0) <= now - published <= timedelta(hours=1):
                continue
            found = set(t.upper() for t in CASHTAG.findall(text)) & symbols
            for ticker in found:
                grouped[ticker][uri] = (author.get('did') or handle, published, href)
    out=[]
    # Single record per ticker per UTC hour; avoids flooding radar with each post.
    for ticker, mentions in grouped.items():
        latest=max(mentions.values(), key=lambda x:x[1])
        author_count=len({v[0] for v in mentions.values()})
        summary=(f'Public Bluesky monitored-account sample: ${ticker} appeared in '
                 f'{len(mentions)} distinct post(s) by {author_count} public author(s) '
                 'within the last 60 minutes. Cashtag matches only; excludes reposts. '
                 'NOT total platform mentions, acceleration, verified sentiment, buying, or a trading signal.')
        out.append({'asset': ticker, 'asset_class':'stock', 'source':'social',
                    'direction':'neutral', 'strength':min(.35, .10 + .02*author_count),
                    'event_id':'bsky-social:'+ticker+':'+now.strftime('%Y%m%d%H'),
                    'observed_at':now.isoformat(), 'published_at':latest[1].isoformat(),
                    'source_url':latest[2], 'summary':summary[:1200]})
    return out


def run(handles, symbols, *, now=None, opener=urlopen, pause_seconds=1.0):
    handles=validate_social_accounts(handles); symbols=validate_cashtags(symbols)
    if not handles or not symbols: return [], []
    feeds={}; errors=[]
    for i,handle in enumerate(handles):
        if i and pause_seconds: time.sleep(pause_seconds)
        try: feeds[handle]=fetch_feed(handle,opener=opener)
        except Exception as exc:
            # Endpoint may respond 403/429; report failure, do not fabricate attention.
            errors.append({'provider':'bluesky','handle':handle,'reason':type(exc).__name__})
    return observe_accounts(feeds,symbols,now),errors
