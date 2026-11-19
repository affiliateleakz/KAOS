import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_coinbase as routes


class Cursor:
    async def to_list(self,**kwargs):
        return [{'size':'1','price':'100','commission':'0.1'}]


@pytest.mark.parametrize('product,fee_currency,accepted',[('BTC-USD','USD',True),('ETH-USD','USD',False),('BTC-USD','BTC',False)])
def test_quote_sized_fills_convert_to_base_and_check_identity(monkeypatch,product,fee_currency,accepted):
    fill={'order_id':'order1','trade_id':'trade1','size':'100','price':'100','commission':'0.1',
          'size_in_quote':True,'product_id':product,'side':'BUY','commission_currency':fee_currency}
    intent={'_id':'intent','client_order_id':'buy','order_id':'order1','user_id':'u','product_id':'BTC-USD','side':'BUY'}
    ledger=SimpleNamespace(find_one=AsyncMock(return_value=None),insert_one=AsyncMock(),find=lambda *_:Cursor())
    db=SimpleNamespace(coinbase_order_intents=SimpleNamespace(find_one=AsyncMock(return_value=intent),update_one=AsyncMock()),
        coinbase_trade_fills=ledger)
    monkeypatch.setattr(routes,'db',db)
    monkeypatch.setattr(routes,'connection',AsyncMock(return_value={}))
    monkeypatch.setattr(routes,'make_client',lambda _:SimpleNamespace(get_order=lambda _:{'order':{'order_id':'order1','status':'FILLED','filled_size':'1'}},get_fills=lambda **kw:{'fills':[fill]}))
    if accepted:
        result=asyncio.run(routes.reconcile_order('u','buy'))
        assert result['filled_size']=='1' and result['notional']=='100'
        assert ledger.insert_one.call_args.args[0]['size']=='1'
    else:
        with pytest.raises(HTTPException):asyncio.run(routes.reconcile_order('u','buy'))
        ledger.insert_one.assert_not_awaited()
