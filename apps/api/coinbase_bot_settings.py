"""Translate the existing extension controls into explicit Coinbase spot limits."""
from decimal import Decimal, InvalidOperation


def money(value, label, *, positive=False):
    if isinstance(value, bool):raise ValueError(label+' must be a dollar amount')
    try:amount=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):raise ValueError(label+' must be a dollar amount')
    try:
        valid=amount.is_finite() and amount>=0 and (not positive or amount>0) and amount==amount.quantize(Decimal('.01'))
    except InvalidOperation:valid=False
    if not valid:raise ValueError(label+' must be a valid whole-cent dollar amount')
    return format(amount,'f')


def normalize(settings,products,chart_limit):
    if not isinstance(settings,dict):raise ValueError('Existing bot settings are required')
    if settings.get('martingale') is not False:raise ValueError('Turn Martingale off in Risk Controls for Coinbase spot trading')
    if settings.get('compound') is not False:raise ValueError('Turn Compounding off in Risk Controls for Coinbase spot trading')
    count=settings.get('chartCount')
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=min(4,chart_limit):
        raise ValueError('Chart count exceeds this membership')
    import re
    if (not isinstance(products,list) or len(products)!=count
            or any(not isinstance(p,str) or not re.fullmatch(r'[A-Z0-9]{2,20}-USD',p) for p in products) or len(set(products))!=count):
        raise ValueError('Choose one distinct Coinbase USD spot market for each selected chart')
    slots=settings.get('strategySlots')
    if not isinstance(slots,list) or len(slots)!=count or any(not isinstance(s,dict) or s.get('profileId')!='legacy7b' for s in slots):
        raise ValueError('Select KAOS Strategy for every Coinbase chart; custom and AI profiles are not supported by this spot runner')
    result={'amount':money(settings.get('amount'),'Trade Amount',positive=True),
            'profitTarget':money(settings.get('profitTarget'),'Profit Target'),
            'dailyLossLimit':money(settings.get('dailyLossLimit'),'Loss Limit'),
            'chartCount':count,'products':products,'strategy':'KAOS_STRATEGY_SR1.1',
            'maxExposureUsd':format(Decimal(money(settings.get('amount'),'Trade Amount',positive=True))*count,'f'),
            'martingale':False,'compound':False,'autoCooldownOn':settings.get('autoCooldownOn') is True}
    for key,maximum in (('maxLossStreak',20),('cooldownAfterLoss',600)):
        value=settings.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=maximum:
            raise ValueError(key+' is missing or invalid in the bot settings')
        result[key]=value
    return result
