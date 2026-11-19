"""Read-only, timestamp-checked OPRA contracts. Never submits broker orders."""
import math
import re
from datetime import datetime,timezone,timedelta
from radar_sources import Sources,SourceIssue,timestamp
import radar_settings


def number(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (TypeError,ValueError):return None


def contracts(underlying,direction,snapshots,price,now):
    wanted='C' if direction=='BUY' else 'P';rows=[]
    for symbol,snapshot in snapshots.items():
        match=re.fullmatch(re.escape(underlying)+r'(\d{6})([CP])(\d{8})',symbol)
        if not match or match[2]!=wanted or not isinstance(snapshot,dict):continue
        try:
            expiry=datetime.strptime(match[1],'%y%m%d').replace(tzinfo=timezone.utc)
            dte=(expiry.date()-now.date()).days
            strike=int(match[3])/1000
            quote=snapshot['latestQuote'];stamp=timestamp(quote['t'])
            if not 0<=(now-stamp).total_seconds()<=120 or not 7<=dte<=45 or not .9<=strike/price<=1.1:continue
            bid,ask=number(quote.get('bp')),number(quote.get('ap'))
            delta=number((snapshot.get('greeks') or {}).get('delta'))
            if bid is None or ask is None or not 0<bid<=ask or delta is None or not .3<=abs(delta)<=.7:continue
            if direction=='BUY' and delta<=0 or direction=='SELL' and delta>=0:continue
            if not (number(quote.get('bs')) or 0)>0 or not (number(quote.get('as')) or 0)>0:continue
            spread=(ask-bid)/((bid+ask)/2)
            if spread>.15:continue
            rows.append({'contract':symbol,'type':'CALL' if wanted=='C' else 'PUT',
                'strike':strike,'expiry':expiry.date().isoformat(),'bid':bid,'ask':ask,
                'quote_time':stamp.isoformat(),'delta':delta,'spread_fraction':spread,
                'source':'Alpaca OPRA','days_to_expiry':dte})
        except (KeyError,ValueError,TypeError,ZeroDivisionError):continue
    return sorted(rows,key=lambda r:(r['spread_fraction'],abs(abs(r['delta'])-.5)))


async def chain(underlying,direction,price,now):
    cfg=await radar_settings.settings('options_data')
    if not cfg.get('enabled',True) or not cfg.get('api_key') or not cfg.get('api_secret') or cfg.get('configuration_error'):
        return None,'Options require owner-configured OPRA market data. No options contracts were invented.'
    session=Sources({})
    try:
        data=await session.request('GET',f'https://data.alpaca.markets/v1beta1/options/snapshots/{underlying}',
            headers={'APCA-API-KEY-ID':cfg['api_key'],'APCA-API-SECRET-KEY':cfg['api_secret']},params={
                'feed':'opra','type':'call' if direction=='BUY' else 'put','limit':100,
                'expiration_date_gte':(now+timedelta(days=7)).date().isoformat(),
                'expiration_date_lte':(now+timedelta(days=45)).date().isoformat(),
                'strike_price_gte':round(price*.9,2),'strike_price_lte':round(price*1.1,2)})
        rows=contracts(underlying,direction,data.get('snapshots',{}),price,now)
        if not rows:return None,'No fresh, sufficiently tight OPRA contract met the options filters.'
        return rows[0],'First 100 returned contracts only; underlying score is not an options win probability.'
    except (SourceIssue,ValueError,TypeError,AttributeError):
        return None,'OPRA chain is unavailable. Check the owner’s market-data access.'
    finally:await session.close()
