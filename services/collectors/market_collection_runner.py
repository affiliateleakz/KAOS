"""KAOS 3.0 multi-provider research runner, no trading/order functions.

Runs once by default, or every N seconds when supervised on an external VPS.
Credentials belong in worker environment variables, not website/mobile JS.
Each provider's observations are neutral or descriptive, never executable orders.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from collector_common import submit
from alpaca_stocks import run as run_stocks, validate_symbols
from tradier_options import run as run_options, validate_symbol
from options_activity import run as run_option_activity, save_state as save_activity_state
from binance_spot import fetch as fetch_crypto, observe as observe_crypto
from dexscreener_pairs import fetch as fetch_dex, observe as observe_dex
from gdelt_news import validate_watchlist as validate_news, run as run_news
from sec_edgar_filings import validate_watchlist as validate_sec, run as run_sec
from sec_insider_transactions import run as run_insider
from ethereum_worker import scan_safe_blocks, save_state
from sec_13f_holdings import validate_managers, run as run_13f
from bluesky_social import validate_social_accounts, validate_cashtags, run as run_social
from bluesky_search import run as run_social_search


def load_config(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(doc, dict): raise ValueError('Configuration must be JSON object')
    config = {}
    for name, limit in [('stocks', 150), ('etfs', 150), ('options_underlyings', 100),
                        ('crypto_spot', 150), ('dex_queries', 20)]:
        raw = doc.get(name, [])
        if not isinstance(raw, list) or len(raw) > limit or any(not isinstance(x, str) for x in raw):
            raise ValueError(f'{name}: expected at most {limit} strings')
        values = list(dict.fromkeys(x.strip().upper() if name != 'dex_queries'
                                    else x.strip() for x in raw))
        if any(not x for x in values): raise ValueError(f'{name}: empty string')
        if name in {'stocks', 'etfs', 'crypto_spot'} and values:
            if name == 'crypto_spot':
                from binance_spot import fetch
                if any(not x.isalnum() or len(x) > 24 for x in values):
                    raise ValueError('Invalid crypto spot symbol')
            else: validate_symbols(values)
        if name == 'options_underlyings':
            values = [validate_symbol(v) for v in values]
        if name == 'dex_queries' and any(len(q) > 80 for q in values):
            raise ValueError('DEX query too long')
        config[name] = values
    if not set(config['etfs']).issubset(set(config['stocks'])):
        raise ValueError('ETFs must also be included in stocks')
    config['news_watchlist'] = validate_news(doc.get('news_watchlist', []))
    config['sec_watchlist'] = validate_sec(doc.get('sec_watchlist', []))
    activity = doc.get('options_activity_underlyings', [])
    if not isinstance(activity, list) or len(activity)>30 or any(not isinstance(x,str) for x in activity):
        raise ValueError('options_activity_underlyings: expected at most 30 strings')
    config['options_activity_underlyings'] = list(dict.fromkeys(validate_symbol(x) for x in activity))
    config['institutional_managers'] = validate_managers(doc.get('institutional_managers', []))
    config['social_accounts'] = validate_social_accounts(doc.get('social_accounts', []))
    config['social_cashtags'] = validate_cashtags(doc.get('social_cashtags', []))
    config['social_search_cashtags'] = validate_cashtags(doc.get('social_search_cashtags', []))
    if len(config['social_search_cashtags']) > 20:
        raise ValueError('social_search_cashtags: maximum 20 symbols')
    # Optional native ETH whale scanner. One safe block per cycle; no historical claim.
    config['eth_whales_enabled'] = doc.get('eth_whales_enabled', False)
    config['eth_whales_min_eth'] = doc.get('eth_whales_min_eth', 500)
    if not isinstance(config['eth_whales_enabled'], bool):
        raise ValueError('eth_whales_enabled must be boolean')
    if isinstance(config['eth_whales_min_eth'], bool) or not isinstance(config['eth_whales_min_eth'], (int,float)) or not 1 <= config['eth_whales_min_eth'] <= 1000000:
        raise ValueError('eth_whales_min_eth must be in 1..1000000')
    config['alpaca_feed'] = doc.get('alpaca_feed', 'iex')
    if config['alpaca_feed'] not in {'iex', 'sip'}: raise ValueError('Invalid Alpaca feed')
    config['tradier_sandbox'] = doc.get('tradier_sandbox', True)
    if not isinstance(config['tradier_sandbox'], bool): raise ValueError('tradier_sandbox must be boolean')
    return config


def collect_once(config, pause=.5, *, include_news=True, include_sec=True, include_13f=True, include_social=True):
    """Return observations and explicit issues; a failed source does not fake data."""
    if not 0 <= pause <= 10: raise ValueError('Pause out of range')
    observations, issues = [], []
    config['_ethereum_checkpoint_pending'] = None
    config['_options_activity_pending'] = None
    now = datetime.now(timezone.utc)
    if config['stocks']:
        key, secret = os.getenv('APCA_API_KEY_ID'), os.getenv('APCA_API_SECRET_KEY')
        if not key or not secret:
            issues.append({'provider': 'alpaca', 'reason': 'missing_stock_provider_credentials'})
        else:
            items, errors = run_stocks(config['stocks'], key, secret,
                                       config['etfs'], config['alpaca_feed'], now=now)
            observations.extend(items)
            issues.extend({'provider': 'alpaca', **e} for e in errors)
    if config['options_underlyings']:
        token = os.getenv('TRADIER_TOKEN')
        if not token:
            issues.append({'provider': 'tradier', 'reason': 'missing_options_provider_token'})
        else:
            items, errors = run_options(config['options_underlyings'], token,
                                       config['tradier_sandbox'], now=now)
            observations.extend(items)
            issues.extend({'provider': 'tradier', **e} for e in errors)
    # Optional incremental options activity comparison. State is NOT written here;
    # only commit after the ingestion API accepts all evidence in this cycle.
    if config['options_activity_underlyings']:
        token = os.getenv('TRADIER_TOKEN')
        if not token:
            issues.append({'provider':'options_activity','reason':'missing_options_provider_token'})
        else:
            try:
                state_path=os.getenv('KAOS_OPTIONS_ACTIVITY_STATE','./options_activity_state.json')
                activity, errors, pending = run_option_activity(
                    config['options_activity_underlyings'],token,
                    state_path=state_path,now=now,sandbox=config['tradier_sandbox'],pause_seconds=max(.5,pause))
                observations.extend(activity)
                issues.extend(errors)
                if len(errors)<len(config['options_activity_underlyings']):
                    config['_options_activity_pending'] = pending
            except Exception as exc:
                issues.append({'provider':'options_activity','reason':type(exc).__name__+'_scanner_error'})
    for symbol in config['crypto_spot']:
        try:
            candles, url = fetch_crypto(symbol)
            item = observe_crypto(symbol, candles, url, now)
            if item:
                observations.append(item)
            else:
                issues.append({'provider': 'binance', 'symbol': symbol, 'reason': 'stale_or_insufficient_bars'})
        except Exception as e:
            issues.append({'provider': 'binance', 'symbol': symbol, 'reason': str(e)})
        time.sleep(pause)
    for query in config['dex_queries']:
        try:
            pairs, url = fetch_dex(query)
            observations.extend(observe_dex(pairs, url, now))
        except Exception as e:
            issues.append({'provider': 'dexscreener', 'query': query, 'reason': str(e)})
        time.sleep(pause)
    if include_news and config['news_watchlist']:
        items, errors = run_news(config['news_watchlist'], now=now, pause_seconds=max(1.,pause))
        observations.extend(items)
        issues.extend(errors)
    if include_sec and config['sec_watchlist']:
        items, errors = run_sec(config['sec_watchlist'], now=now, pause_seconds=max(1.,pause))
        observations.extend(items)
        issues.extend(errors)
        # Ownership *transaction* parser is separate from Form 4 filing discovery.
        # Avoid signing P/S merely because a Form 4 was submitted.
        items, errors = run_insider(config['sec_watchlist'], now=now, pause_seconds=max(1.,pause))
        observations.extend(items)
        issues.extend(errors)
    if include_13f and config['institutional_managers']:
        items, errors = run_13f(config['institutional_managers'], now=now,
                                pause_seconds=max(1., pause))
        observations.extend(items)
        issues.extend(errors)
    if include_social and config['social_accounts'] and config['social_cashtags']:
        items, errors = run_social(config['social_accounts'], config['social_cashtags'],
                                   now=now, pause_seconds=max(1., pause))
        observations.extend(items)
        issues.extend(errors)
    if include_social and config['social_search_cashtags']:
        items, errors = run_social_search(config['social_search_cashtags'], now=now,
                                           pause_seconds=max(1.5,pause))
        observations.extend(items)
        issues.extend(errors)
    if config.get('eth_whales_enabled'):
        url = os.getenv('ETH_RPC_URL','')
        if not url:
            issues.append({'provider':'ethereum','reason':'missing_ETH_RPC_URL'})
        else:
            try:
                new_items, eth_progress = scan_safe_blocks(url,
                   os.getenv('KAOS_ETH_CHECKPOINT','./ethereum_safe_checkpoint.json'),
                   config['eth_whales_min_eth'])
                observations.extend(new_items)
                if eth_progress['processed_blocks']:
                    config['_ethereum_checkpoint_pending'] = eth_progress['last_safe_block']
                if not eth_progress['caught_up']:
                    issues.append({'provider':'ethereum','reason':'backlog_remaining',
                                   'last_safe_block':eth_progress['last_safe_block'],
                                   'latest_safe_block':eth_progress['latest_safe_block']})
            except Exception as e:
                # RPC URLs can include private project tokens; never leak URLs/error bodies.
                issues.append({'provider':'ethereum','reason':type(e).__name__+'_rpc_error'})
    # Every provider assigns deterministic event ids. Duplicate query results are merged.
    observations = list({(item['source'], item['event_id']): item
                         for item in observations}.values())
    return observations, issues


def main():
    parser = argparse.ArgumentParser(description='KAOS 3.0 research collection worker')
    parser.add_argument('--config', default='market_universe.example.json')
    parser.add_argument('--dry-run', action='store_true', help='Query feeds, do NOT send results to backend')
    parser.add_argument('--loop', action='store_true', help='Keep collecting when hosted under supervisor')
    parser.add_argument('--interval', type=int, default=300, help='Seconds; minimum 60')
    parser.add_argument('--pause', type=float, default=.5, help='Seconds between public provider requests')
    parser.add_argument('--api', default=os.getenv('KAOS_API_BASE', ''))
    parser.add_argument('--news-minutes',type=int,default=15,help='Minimum interval between GDELT queries (>=15)')
    parser.add_argument('--sec-minutes',type=int,default=60,help='Minimum interval between SEC filing queries (>=60)')
    parser.add_argument('--institutional-minutes', type=int, default=360, help='Minimum 13F SEC polling interval (>=360)')
    parser.add_argument('--social-minutes', type=int, default=15, help='Minimum public social sampling interval (>=15)')
    args = parser.parse_args()
    if args.loop and args.interval < 60:
        parser.error('Collection interval must be at least 60 seconds')
    if args.news_minutes < 15 or args.sec_minutes < 60 or args.institutional_minutes < 360 or args.social_minutes < 15:
        parser.error('Minimum polling: news 15, SEC 60, institutions 360, social 15 minutes')
    config = load_config(args.config)
    last_news = last_sec = last_institutional = last_social = None
    while True:
        clock = time.monotonic()
        due_news = last_news is None or clock-last_news>=args.news_minutes*60
        due_sec = last_sec is None or clock-last_sec>=args.sec_minutes*60
        due_institutional = last_institutional is None or clock-last_institutional>=args.institutional_minutes*60
        due_social = last_social is None or clock-last_social>=args.social_minutes*60
        observations, issues = collect_once(config, args.pause, include_news=due_news, include_sec=due_sec,
                                            include_13f=due_institutional, include_social=due_social)
        if due_news: last_news = clock
        if due_sec: last_sec = clock
        if due_institutional: last_institutional = clock
        if due_social: last_social = clock
        report = {'time': datetime.now(timezone.utc).isoformat(),
                  'requested_symbols': {k: len(v) for k, v in config.items() if isinstance(v, list)},
                  'observations': len(observations), 'issues': issues,
                  'mode': 'dry_run' if args.dry_run else 'research_only'}
        delivery_ok = not observations
        if args.dry_run:
            report['sample'] = observations[:5]
        elif observations:
            if not args.api:
                report['delivery_error'] = 'KAOS_API_BASE missing; no observations submitted'
            else:
                try:
                    report['delivery'] = submit(observations, args.api)
                    delivery_ok = report['delivery']['submitted'] == len(observations)
                except Exception as e: report['delivery_error'] = str(e)
        # Do not skip on-chain whale transactions if KAOS ingestion failed.
        # Dry runs never advance checkpoints.
        if not args.dry_run and delivery_ok and config.get('_ethereum_checkpoint_pending') is not None:
            save_state(os.getenv('KAOS_ETH_CHECKPOINT','./ethereum_safe_checkpoint.json'),
                       config['_ethereum_checkpoint_pending'])
            report['ethereum_checkpoint_committed'] = True
        if not args.dry_run and delivery_ok and config.get('_options_activity_pending') is not None:
            try:
                save_activity_state(os.getenv('KAOS_OPTIONS_ACTIVITY_STATE','./options_activity_state.json'),
                                    config['_options_activity_pending'])
                report['options_activity_checkpoint_committed'] = True
            except Exception as exc:
                report['options_activity_checkpoint_error'] = type(exc).__name__
        print(json.dumps(report), flush=True)
        if not args.loop: return
        time.sleep(args.interval)

if __name__ == '__main__': main()
