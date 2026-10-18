"""Research-only US listed options chain liquidity scanner via Tradier.

Uses only GET market-data endpoints; never submits option orders. A high
volume/open-interest ratio is NOT evidence of directional buying. Data is
summarized neutrally and quote quality is screened.
"""
import argparse
import json
import os
import re
import time
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from collector_common import positive_float, read_json, require_token, submit, utc

LIVE_BASE = 'https://api.tradier.com/v1'
SANDBOX_BASE = 'https://sandbox.tradier.com/v1'
VALID_SYMBOL = re.compile(r'^[A-Z][A-Z0-9.]{0,11}$')


def validate_symbol(symbol):
    symbol = str(symbol).upper().strip()
    if not VALID_SYMBOL.fullmatch(symbol):
        raise ValueError('Invalid underlying symbol')
    return symbol


def market_get(endpoint, symbol, token, *, sandbox=False, parameters=None, opener=urlopen):
    symbol = validate_symbol(symbol)
    require_token(token, 'TRADIER_TOKEN')
    if endpoint not in {'expirations', 'chains'}:
        raise ValueError('Only market-data endpoints are allowed')
    params = {'symbol': symbol, **(parameters or {})}
    base = SANDBOX_BASE if sandbox else LIVE_BASE
    return read_json(base + '/markets/options/' + endpoint + '?' + urlencode(params),
                     headers={'Authorization': 'Bearer ' + token,
                              'Accept': 'application/json'}, opener=opener)


def next_expiration(data, today=None):
    today = today or datetime.now(timezone.utc).date()
    raw = (data.get('expirations') or {}).get('date', [])
    if isinstance(raw, str): raw = [raw]
    candidates = []
    for value in raw or []:
        try:
            value = str(value)
            dt = date.fromisoformat(value)
            if dt >= today: candidates.append(dt)
        except (ValueError, TypeError):
            continue
    return min(candidates).isoformat() if candidates else None


def scan_chain(underlying, expiration, payload, now=None, *, sandbox=False,
               max_contracts=15, min_volume=25, min_oi=50):
    """Neutral observations for active contracts and the underlying.

    An option's volume/OI does not say whether buyers or sellers initiated,
    and OI may lag; quote spread is only a liquidity heuristic.
    """
    underlying = validate_symbol(underlying)
    now = utc(now or datetime.now(timezone.utc))
    raw = (payload.get('options') or {}).get('option', [])
    if isinstance(raw, dict): raw = [raw]
    if not isinstance(raw, list):
        raise ValueError('Unexpected Tradier chain response')
    ranked = []
    for contract in raw:
        if not isinstance(contract, dict): continue
        contract_symbol = str(contract.get('symbol') or '')
        option_type = str(contract.get('option_type', '')).lower()
        if not re.fullmatch(r'[A-Z0-9.]{1,40}', contract_symbol) or option_type not in {'call', 'put'}:
            continue
        volume = positive_float(contract.get('volume'))
        oi = positive_float(contract.get('open_interest'))
        bid = positive_float(contract.get('bid'))
        ask = positive_float(contract.get('ask'))
        strike = positive_float(contract.get('strike'))
        if volume < min_volume or oi < min_oi or bid <= 0 or ask < bid or strike <= 0:
            continue
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid if mid else 1
        if spread_pct > .35:
            continue
        ratio = volume / max(oi, 1)
        ranked.append({'symbol': contract_symbol, 'type': option_type,
                       'strike': strike, 'volume': int(volume), 'oi': int(oi),
                       'ratio': ratio, 'spread_pct': spread_pct})
    ranked.sort(key=lambda x: (x['ratio'], x['volume']), reverse=True)
    asof = now.isoformat()
    hour_bucket = int(now.timestamp() // 3600)
    environment = 'sandbox/delayed' if sandbox else 'production/entitlement-dependent'
    source_url = 'https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains'
    result = []
    for c in ranked[:max_contracts]:
        result.append({
            'asset': c['symbol'], 'asset_class': 'option', 'source': 'options_flow',
            'direction': 'neutral', 'strength': round(min(1., c['ratio'] / 3), 4),
            'event_id': f'tradier:{int(sandbox)}:{c["symbol"]}:{hour_bucket}',
            'observed_at': asof, 'published_at': asof, 'source_url': source_url,
            'summary': (f'Tradier {environment} option chain snapshot {underlying} '
                        f'{expiration} {c["type"].upper()} {c["strike"]:g}: '
                        f'volume {c["volume"]}, reported OI {c["oi"]}, '
                        f'volume/OI {c["ratio"]:.2f}, bid/ask spread {c["spread_pct"]:.1%}. '
                        'Direction unknown; not proof of unusual institutional buying. '
                        'Snapshot retrieved at observed_at, not trade timestamp.')
        })
    if ranked:
        selected = ranked[:max_contracts]
        call_volume = sum(c['volume'] for c in selected if c['type'] == 'call')
        put_volume = sum(c['volume'] for c in selected if c['type'] == 'put')
        result.append({
            'asset': underlying, 'asset_class': 'stock', 'source': 'options_flow',
            'direction': 'neutral',
            'strength': round(min(1., max(c['ratio'] for c in selected) / 3), 4),
            'event_id': f'tradier:{int(sandbox)}:{underlying}:{expiration}:{hour_bucket}:summary',
            'observed_at': asof, 'published_at': asof, 'source_url': source_url,
            'summary': (f'Tradier {environment} {underlying} option chain {expiration}: '
                        f'{len(selected)} liquid active contracts screened; '
                        f'call volume {call_volume}; put volume {put_volume} '
                        '(selected contracts only, NOT full-chain put/call ratio). '
                        'Neutral research signal, snapshot time only.')
        })
    return result


def run(symbols, token, sandbox=False, now=None, opener=urlopen, pause_seconds=.5):
    now = utc(now or datetime.now(timezone.utc))
    symbols = list(dict.fromkeys(validate_symbol(sym) for sym in symbols))
    if not symbols or len(symbols) > 100: raise ValueError('Supply 1-100 underlying symbols')
    observations, problems = [], []
    for i, sym in enumerate(symbols):
        if i and pause_seconds:
            time.sleep(pause_seconds)
        try:
            dates = market_get('expirations', sym, token, sandbox=sandbox,
                               parameters={'includeAllRoots': 'false'}, opener=opener)
            expiry = next_expiration(dates, now.date())
            if not expiry:
                problems.append({'symbol': sym, 'reason': 'no_future_listed_expiration'})
                continue
            chain = market_get('chains', sym, token, sandbox=sandbox,
                               parameters={'expiration': expiry, 'greeks': 'true'}, opener=opener)
            results = scan_chain(sym, expiry, chain, now, sandbox=sandbox)
            if results:
                observations.extend(results)
            else:
                problems.append({'symbol': sym, 'reason': 'no_liquid_contracts_matching_filters'})
        except Exception as exc:
            problems.append({'symbol': sym, 'reason': str(exc)})
    return observations, problems


def main():
    parser = argparse.ArgumentParser(description='KAOS research-only options chain scanner')
    parser.add_argument('--symbols', default='AAPL,NVDA,SPY')
    parser.add_argument('--sandbox', action='store_true', help='Delayed Tradier sandbox feed')
    parser.add_argument('--api', default=os.getenv('KAOS_API_BASE', ''))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    token = require_token(os.getenv('TRADIER_TOKEN'), 'TRADIER_TOKEN')
    observations, problems = run(args.symbols.split(','), token, sandbox=args.sandbox)
    summary = {'provider': 'tradier', 'feed': 'sandbox_delayed' if args.sandbox else 'live_entitlement_dependent',
               'observations': len(observations), 'issues': problems}
    if args.dry_run:
        summary['items'] = observations
    else:
        summary['delivery'] = submit(observations, args.api)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
