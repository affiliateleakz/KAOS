import asyncio
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from coinbase_bot_settings import normalize
from coinbase_auto_feed import TradeFeed
from coinbase_entry_limits import reserve
from coinbase_auto_worker import session_result


def controls():
    return {'amount':17.25,'chartCount':2,'martingale':False,'compound':False,'maxLossStreak':3,
            'cooldownAfterLoss':45,'autoCooldownOn':True,'profitTarget':80,'dailyLossLimit':35,
            'strategySlots':[{'slot':0,'profileId':'legacy7b'},{'slot':1,'profileId':'legacy7b'}]}


def test_existing_bot_controls_map_without_another_money_setting():
    source=controls();before=deepcopy(source)
    result=normalize(source,['BTC-USD','ETH-USD'],4)
    assert result['amount']=='17.25' and result['maxExposureUsd']=='34.50'
    assert result['dailyLossLimit']=='35' and result['profitTarget']=='80'
    assert result['maxLossStreak']==3 and result['cooldownAfterLoss']==45
    assert source==before


@pytest.mark.parametrize('field,value',[('amount',None),('amount',float('nan')),('amount',0),('amount',True),
    ('amount',1.001),('amount','1e1000'),('martingale',True),('compound',True),('chartCount',True),
    ('maxLossStreak',-1),('cooldownAfterLoss',None),('dailyLossLimit',None),('profitTarget',-1)])
def test_missing_or_unsupported_settings_never_get_substituted(field,value):
    settings=controls();settings[field]=value
    with pytest.raises(ValueError):normalize(settings,['BTC-USD','ETH-USD'],4)


def test_membership_products_and_custom_strategy_cannot_be_bypassed():
    with pytest.raises(ValueError):normalize(controls(),['BTC-USD','ETH-USD'],1)
    for products in (['BTC-USD','BTC-USD'],['BTC-USD','ETHUSD_otc'],['BTC-USD',{}]):
        with pytest.raises(ValueError):normalize(controls(),products,4)
    settings=controls();settings['strategySlots'][0]['profileId']='custom1'
    with pytest.raises(ValueError):normalize(settings,['BTC-USD','ETH-USD'],4)


def trade(identifier,ms,price=100):
    return {'trade_id':identifier,'time':datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(),'price':str(price)}


def test_feed_never_fills_missing_buckets_or_uses_partial_start_bucket():
    feed=TradeFeed();base=1700000000000//5000*5000
    assert feed.update([trade(1,base+1000)],base+1000)==[]
    assert feed.update([trade(3,base+6000,102),trade(2,base+3000,101)],base+6000)==[]
    rows=feed.update([trade(4,base+11000,103)],base+11000)
    assert len(rows)==1 and rows[0]['ts']==base+5000 and rows[0]['open']==102
    # No trades in the next interval: the history restarts, it isn't forward-filled.
    rows=feed.update([trade(5,base+21000,104),trade(6,base+26000,105)],base+26000)
    assert rows[-1]['ts']==base+20000 and len(rows)==1


def test_sequence_gap_and_stale_feed_never_produce_a_signal_history():
    feed=TradeFeed();base=1700000000000//5000*5000
    feed.update([trade(1,base)],base)
    with pytest.raises(ValueError,match='gap'):feed.update([trade(3,base+5000)],base+5000)
    assert feed.rows==[]
    with pytest.raises(ValueError,match='stale'):feed.update([trade(4,base+6000)],base+30000)


class Cursor:
    def __init__(self,rows):self.rows=rows
    async def to_list(self,n):return self.rows[:n]


@pytest.mark.parametrize('rows',[[{'reserved_usd':'17.25'},{'reserved_usd':'17.25'}],[{}]])
def test_risk_reservation_refuses_full_or_unknown_exposure(rows):
    slots=SimpleNamespace(find=lambda *_:Cursor(rows),insert_one=AsyncMock())
    db=SimpleNamespace(coinbase_active_slots=slots,coinbase_risk_accounts=SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1))))
    settings=normalize(controls(),['BTC-USD','ETH-USD'],4)
    with pytest.raises(HTTPException):asyncio.run(reserve({'user_id':'u','product_id':'ETH-USD','client_order_id':'cid'},settings,db))
    slots.insert_one.assert_not_awaited()


def test_limits_are_notional_reservations_before_any_provider_submission():
    slots=SimpleNamespace(find=lambda *_:Cursor([{'reserved_usd':'17.25'}]),insert_one=AsyncMock())
    db=SimpleNamespace(coinbase_active_slots=slots,coinbase_risk_accounts=SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1))))
    asyncio.run(reserve({'_id':'u:coinbase:ETH-USD','user_id':'u','product_id':'ETH-USD','client_order_id':'cid'},normalize(controls(),['BTC-USD','ETH-USD'],4),db))
    assert slots.insert_one.call_args.args[0]['reserved_usd']=='17.25'
    assert db.coinbase_risk_accounts.update_one.await_count==2
    query,update=db.coinbase_risk_accounts.update_one.call_args.args
    assert query['notional_cents']=={'$lte':1725}
    assert update['$inc']=={'notional_cents':1725,'position_count':1}


def test_existing_loss_limit_uses_verified_cost_and_current_open_position_mark():
    settings=normalize(controls(),['BTC-USD','ETH-USD'],4);settings['dailyLossLimit']='10'
    intents=[{'client_order_id':'buy','side':'BUY','state':'FILLED','filled_size':'1',
              'fill_notional':'100','fill_fees':'1','product_id':'BTC-USD'}]
    pnl,halt,cooling=session_result(intents,{'BTC-USD':Decimal('85')},{'settings':settings})
    assert pnl==Decimal('-16') and halt and not cooling
    with pytest.raises(ValueError,match='mark'):session_result(intents,{}, {'settings':settings})
