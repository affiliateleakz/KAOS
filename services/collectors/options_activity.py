"""KAOS options activity monitor: incremental chain-volume changes, research only.

A snapshot cannot reveal trade initiator, institution identity, or true
transaction timestamps. Reported exchange option volume is cumulative intraday;
the difference between valid snapshots is merely volume growth.

No option orders are ever created. Durable state is committed separately, only
following successful delivery, by the supervising market_collection_runner.
"""
import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from collector_common import positive_float, require_token, submit, utc
from tradier_options import market_get, next_expiration, validate_symbol

STATE_VERSION = 1
SOURCE_URL = 'https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains'


def _chain_options(response):
    raw = (response.get('options') or {}).get('option', [])
    if isinstance(raw, dict): raw = [raw]
    if not isinstance(raw, list): raise ValueError('Invalid options chain result')
    return raw


def capture(underlying, expiration, payload, *, now=None, sandbox=False):
    """Take a quote snapshot while filtering invalid/illiquid contracts."""
    now=utc(now or datetime.now(timezone.utc))
    underlying=validate_symbol(underlying)
    entries={}
    for quote in _chain_options(payload):
        if not isinstance(quote, dict): continue
        symbol=str(quote.get('symbol') or '')
        side=str(quote.get('option_type') or '').lower()
        if not re.fullmatch(r'[A-Z0-9.]{1,40}',symbol) or side not in ('call','put'): continue
        bid=positive_float(quote.get('bid'))
        ask=positive_float(quote.get('ask'))
        strike=positive_float(quote.get('strike'))
        volume=positive_float(quote.get('volume'))
        oi=positive_float(quote.get('open_interest'))
        if not (bid>0 and ask>=bid and strike>0 and oi>0): continue
        spread=(ask-bid)/((bid+ask)/2)
        if spread>.35: continue
        entries[symbol]={'type':side,'volume':int(volume),'oi':int(oi),
                         'spread':round(spread,4),'strike':strike}
    return {'underlying':underlying,'expiration':expiration,
            'date':now.date().isoformat(),'at':now.isoformat(),
            'sandbox':bool(sandbox),'contracts':entries}


def compare(previous, current, *, min_new_volume=100, min_ratio=.75, min_interval_seconds=60, max_interval_seconds=3600):
    """Return neutral activity observations for volume gains since last snapshot.

    Never compare different sessions, expiries or sandbox environments. Do not
    call observed price/volume changes actual orders or buyer-initiated sweeps.
    """
    if previous is None: return []
    if any(previous.get(field)!=current.get(field) for field in ('underlying','expiration','date','sandbox')):
        return []
    earlier=utc(previous['at']); now=utc(current['at'])
    age=(now-earlier).total_seconds()
    if not min_interval_seconds <= age <= max_interval_seconds: return []
    results=[]
    for symbol, new in current['contracts'].items():
        old=previous.get('contracts',{}).get(symbol)
        if not old: continue
        new_volume=new['volume']-int(old['volume'])
        if new_volume<min_new_volume or new['volume']<old['volume']: continue
        ratio=new_volume/max(1,int(new['oi']))
        if ratio<min_ratio: continue
        research_date=now.isoformat()
        # Neutral signal only: OI is typically not continuously updated and
        # cumulative volume is not unique buyer/seller volume.
        results.append({
            'asset':symbol,'asset_class':'option','source':'options_flow',
            'direction':'neutral','strength':round(min(1,ratio/3),4),
            'event_id':f"option-volume-rise:{int(current['sandbox'])}:{symbol}:{int(now.timestamp())}",
            'observed_at':research_date,'published_at':research_date,
            'source_url':SOURCE_URL,
            'summary':(
                f"Tradier {'sandbox/delayed' if current['sandbox'] else 'entitlement-dependent'} "
                f"{current['underlying']} {current['expiration']} {new['type'].upper()} "
                f"strike {new['strike']:g}: reported contract volume increased "
                f"{new_volume:,} across {int(age/60)} min snapshots; "
                f"volume change / reported OI {ratio:.2f}; "
                f"current bid/ask spread {new['spread']:.1%}. "
                "Not trade-by-trade flow, not proof of institutional buying or direction."
            )
        })
    return results


def read_state(path):
    path=Path(path)
    if not path.exists():return {'version':STATE_VERSION,'snapshots':{}}
    if path.stat().st_size>5_000_000:raise ValueError('Activity state is too large')
    doc=json.loads(path.read_text(encoding='utf-8'))
    if doc.get('version') != STATE_VERSION or not isinstance(doc.get('snapshots'),dict):
        raise ValueError('Activity state has unsupported schema')
    return doc


def save_state(path, doc):
    if doc.get('version')!=STATE_VERSION:raise ValueError('Invalid activity state')
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.kaos-options-',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(doc,stream,separators=(',',':'),allow_nan=False)
            stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def run(symbols, token, *, state_path, now=None, sandbox=True, opener=urlopen, pause_seconds=.5):
    """Return observations, provider errors and *pending* checkpoint (not saved)."""
    import time
    symbols=list(dict.fromkeys(validate_symbol(s) for s in symbols))
    if not symbols or len(symbols)>30:raise ValueError('Supply 1-30 symbols')
    now=utc(now or datetime.now(timezone.utc))
    state=read_state(state_path)
    pending={'version':STATE_VERSION,'snapshots':dict(state['snapshots'])}
    alerts=[];errors=[]
    for index,symbol in enumerate(symbols):
        if index and pause_seconds:time.sleep(pause_seconds)
        try:
            expirations=market_get('expirations',symbol,token,sandbox=sandbox,
                parameters={'includeAllRoots':'false'},opener=opener)
            expiry=next_expiration(expirations,now.date())
            if not expiry:
                errors.append({'provider':'options_activity','symbol':symbol,'reason':'no_expiration'})
                continue
            chain=market_get('chains',symbol,token,sandbox=sandbox,
                parameters={'expiration':expiry,'greeks':'false'},opener=opener)
            snap=capture(symbol,expiry,chain,now=now,sandbox=sandbox)
            key=f'{int(sandbox)}:{symbol}'
            alerts.extend(compare(state['snapshots'].get(key),snap))
            pending['snapshots'][key]=snap
        except Exception as e:
            errors.append({'provider':'options_activity','symbol':symbol,'reason':str(e)})
    return alerts,errors,pending


def main():
    p=argparse.ArgumentParser(description='KAOS options volume-change monitor (research only)')
    p.add_argument('--symbols',default='SPY,AAPL')
    p.add_argument('--state',default=os.getenv('KAOS_OPTIONS_ACTIVITY_STATE','./options_activity_state.json'))
    p.add_argument('--sandbox',action='store_true',default=False)
    p.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    observations,issues,pending=run(args.symbols.split(','),
        require_token(os.getenv('TRADIER_TOKEN'),'TRADIER_TOKEN'),
        state_path=args.state,sandbox=args.sandbox)
    result={'mode':'dry_run' if args.dry_run else 'research_only',
            'alerts':len(observations),'issues':issues}
    if args.dry_run:result['observations']=observations
    else:
        if not args.api:p.error('KAOS_API_BASE is required')
        delivered=submit(observations,args.api) if observations else {'submitted':0}
        if delivered['submitted']!=len(observations):
            raise RuntimeError('Not all alerts delivered; state not advanced')
        save_state(args.state,pending)
        result['delivery']=delivered
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
