"""KAOS 3.0 stock/ETF candle research using Alpaca Market Data (not order APIs).

Requires APCA_API_KEY_ID and APCA_API_SECRET_KEY. Default feed is IEX (one
exchange, not consolidated national volume); SIP requires appropriate access.
Bar timestamps are the beginning of each minute. Only CLOSED bars are evaluated.
"""
import argparse
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from collector_common import positive_float, read_json, require_token, submit, utc

BASE = 'https://data.alpaca.markets/v2/stocks/bars'
VALID_SYMBOL = re.compile(r'^[A-Z][A-Z0-9.]{0,11}$')
FEEDS = {'iex', 'sip'}
TIMEFRAME = '1Min'


def validate_symbols(symbols):
    unique = list(dict.fromkeys(str(s).upper().strip() for s in symbols))
    if not unique or len(unique) > 150 or any(not VALID_SYMBOL.fullmatch(x) for x in unique):
        raise ValueError('Supply 1-150 valid stock/ETF symbols')
    return unique


def fetch_bars(symbols, key, secret, feed='iex', now=None, max_pages=30, opener=urlopen):
    """Alpaca paginates globally by symbol; traverse every page before evaluating.

    Raise an error on incomplete pagination rather than silently omitting symbols.
    Retain the last 80 points per symbol, bounding memory across 150 markets.
    """
    symbols = validate_symbols(symbols)
    if feed not in FEEDS or not 1 <= max_pages <= 100:
        raise ValueError('Unsupported feed or page cap')
    require_token(key, 'APCA_API_KEY_ID')
    require_token(secret, 'APCA_API_SECRET_KEY')
    now = utc(now or datetime.now(timezone.utc))
    start = now - timedelta(days=7)
    bars = {symbol: deque(maxlen=80) for symbol in symbols}
    headers = {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}
    seen_pages = set()
    page_token = None
    for _ in range(max_pages):
        params = {'symbols': ','.join(symbols), 'timeframe': TIMEFRAME,
                  'start': start.isoformat().replace('+00:00', 'Z'),
                  'end': now.isoformat().replace('+00:00', 'Z'),
                  'limit': 10000, 'sort': 'asc', 'feed': feed}
        if page_token:
            params['page_token'] = page_token
        response = read_json(BASE + '?' + urlencode(params), headers=headers, opener=opener)
        if not isinstance(response, dict) or not isinstance(response.get('bars'), dict):
            raise ValueError('Alpaca stock bars response invalid')
        for symbol, points in response['bars'].items():
            if symbol not in bars or not isinstance(points, list):
                continue
            for b in points:
                if isinstance(b, dict) and 't' in b:
                    bars[symbol].append(b)
        page_token = response.get('next_page_token')
        if not page_token:
            return {s: list(points) for s, points in bars.items()}
        if page_token in seen_pages:
            raise ValueError('Alpaca pagination loop detected')
        seen_pages.add(page_token)
    raise ValueError('Alpaca pagination incomplete: reduce batch size or raise --max-pages')


def observe(symbol, points, feed='iex', asset_class='stock', now=None, max_age_minutes=30):
    """Describe completed 1m candles; do not predict profit or submit orders."""
    symbol = validate_symbols([symbol])[0]
    if feed not in FEEDS or asset_class not in {'stock', 'etf'}:
        raise ValueError('Invalid market metadata')
    now = utc(now or datetime.now(timezone.utc))
    accepted = []
    for b in points:
        try:
            start = utc(b['t'])
            close = positive_float(b['c'])
            volume = positive_float(b.get('v', 0))
        except (ValueError, KeyError, TypeError):
            continue
        if close <= 0 or start + timedelta(minutes=1) > now:
            continue  # forming candle, no look-ahead
        accepted.append({'t': start, 'c': close, 'v': volume})
    accepted.sort(key=lambda b: b['t'])
    if len(accepted) < 21:
        return None
    accepted = list({b['t']: b for b in accepted}.values())
    if len(accepted) < 21:
        return None
    last = accepted[-1]
    age_minutes = (now - (last['t'] + timedelta(minutes=1))).total_seconds() / 60
    if not 0 <= age_minutes <= max_age_minutes:
        return None  # market closed / provider delayed / stale feed
    closes = [b['c'] for b in accepted]
    avg20 = sum(closes[-20:]) / 20
    change5 = closes[-1] / closes[-6] - 1
    earlier_volumes = [b['v'] for b in accepted[-21:-1]]
    avg_volume = sum(earlier_volumes) / 20
    volume_ratio = last['v'] / avg_volume if avg_volume else 0
    direction = ('bullish' if closes[-1] > avg20 and change5 > .002 else
                 'bearish' if closes[-1] < avg20 and change5 < -.002 else 'neutral')
    strength = min(1., max(0., abs(change5) * 35) + min(0.3, max(0., volume_ratio - 1) * .05))
    end = last['t'] + timedelta(minutes=1)
    return {
        'asset': symbol, 'asset_class': asset_class, 'source': 'technical',
        'direction': direction, 'strength': round(strength, 4),
        'event_id': f'alpaca:{feed}:1m:{symbol}:{int(last["t"].timestamp())}',
        'observed_at': end.isoformat(), 'published_at': end.isoformat(),
        'source_url': 'https://docs.alpaca.markets/us/reference/stockbars',
        'summary': (f'Alpaca {feed.upper()} (not consolidated if IEX) 1m closed bar: '
                    f'close {closes[-1]:.4g}, SMA20 {avg20:.4g}, 5-bar change {change5:.2%}, '
                    f'volume relative to prior 20 bars {volume_ratio:.2f}x. '
                    'Historical bar, research only; provider entitlement and latency apply.')
    }


def run(symbols, key, secret, etfs=(), feed='iex', now=None, max_pages=30, opener=urlopen, pause_seconds=.35):
    symbols = validate_symbols(symbols)
    etfs = set(validate_symbols(etfs)) if etfs else set()
    if not etfs.issubset(symbols):
        raise ValueError('ETF symbols must also appear in --symbols')
    # Smaller batches avoid missing later symbols due to Alpaca global pagination.
    now = utc(now or datetime.now(timezone.utc))
    observations, errors = [], []
    for offset in range(0, len(symbols), 10):
        if offset and pause_seconds:
            time.sleep(pause_seconds)
        chunk = symbols[offset:offset + 10]
        try:
            bars = fetch_bars(chunk, key, secret, feed=feed, now=now,
                              max_pages=max_pages, opener=opener)
            for sym in chunk:
                result = observe(sym, bars.get(sym, []), feed=feed,
                                 asset_class='etf' if sym in etfs else 'stock', now=now)
                if result:
                    observations.append(result)
                else:
                    errors.append({'symbol': sym, 'reason': 'stale_or_insufficient_closed_bars'})
        except Exception as exc:
            errors.append({'symbols': chunk, 'reason': str(exc)})
    return observations, errors


def main():
    parser = argparse.ArgumentParser(description='KAOS research-only stock/ETF collector')
    parser.add_argument('--symbols', default='AAPL,MSFT,NVDA,SPY,QQQ')
    parser.add_argument('--etfs', default='SPY,QQQ')
    parser.add_argument('--feed', choices=sorted(FEEDS), default='iex')
    parser.add_argument('--api', default=os.getenv('KAOS_API_BASE', ''))
    parser.add_argument('--max-pages', type=int, default=30)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    symbols = validate_symbols(args.symbols.split(','))
    etfs = [x.strip() for x in args.etfs.split(',') if x.strip()]
    key = require_token(os.getenv('APCA_API_KEY_ID'), 'APCA_API_KEY_ID')
    secret = require_token(os.getenv('APCA_API_SECRET_KEY'), 'APCA_API_SECRET_KEY')
    observations, errors = run(symbols, key, secret, etfs, args.feed, max_pages=args.max_pages)
    summary = {'provider': 'alpaca', 'feed': args.feed, 'requested': len(symbols),
               'fresh_observations': len(observations), 'issues': errors}
    if args.dry_run:
        summary['observations'] = observations
    else:
        summary['delivery'] = submit(observations, args.api)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
