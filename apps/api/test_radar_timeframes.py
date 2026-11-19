"""Long-horizon plans must not inherit intraday freshness or train its model."""
import asyncio
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from radar_signals import assess
from radar_opportunities import setup,OpportunityInput
from test_radar_opportunities import quote

NOW=datetime.now(timezone.utc)


def test_closed_market_daily_candles_and_incomplete_bar_exclusion():
    close=NOW.timestamp()-2*86400
    rows=[[close-(80-i)*86400,99+i,101+i,100+i,100.5+i,100] for i in range(80)]
    rows.append([NOW.timestamp(),1,10000,2,9000,100])
    report=assess(rows,NOW.timestamp(),86400,True)
    assert len(report['feature_vector'])==7 and report['price']==179.5
    assert 'feature_vector' not in assess(rows,NOW.timestamp())
    assert 'feature_vector' not in assess(rows,(NOW+timedelta(days=7)).timestamp(),86400,True)


@pytest.mark.parametrize('frame',['daily','weekly','monthly'])
def test_closed_session_plans_have_timeframe_levels_and_remain_non_executable(frame):
    q=quote(source_time=(NOW-timedelta(days=2)).isoformat(),planning=True,timeframe=frame,horizon=frame)
    row=setup({'symbol':'AAPL','asset_class':'stock'},q,{},NOW)
    assert row and row['planning'] and row['timeframe']==frame
    assert row['execution_enabled'] is False and not row['ai_confirmed']
    assert 'revalidate' in row['plan_note'] and row['reference_stop']<100<row['reference_target']
    q['planning']=False
    assert setup({'symbol':'AAPL','asset_class':'stock'},q,{},NOW) is None


def test_timeframe_validation():
    assert OpportunityInput().timeframe=='daily'
    with pytest.raises(ValidationError):OpportunityInput(timeframe='hourly')


def test_plans_do_not_train_or_query_intraday_models(monkeypatch):
    import kaos_radar_ai as native
    from test_kaos_radar_ai import Samples
    models=SimpleNamespace(find_one=AsyncMock(return_value=None))
    samples=Samples()
    monkeypatch.setattr(native,'db',SimpleNamespace(kaos_radar_samples=samples,kaos_radar_models=models))
    report=asyncio.run(native.assessment({'symbol':'AAPL','asset_class':'stock'},
        quote(planning=True,timeframe='monthly'),[],NOW))
    assert report['model_state']=='collecting'
    assert models.find_one.call_args.args[0]['_id']=='stock:monthly'
    assert samples.writes[0][1]['$setOnInsert']['profile']=='stock:monthly'


def test_options_plans_work_without_claiming_fresh_contracts(monkeypatch):
    import radar_opportunities as scanner
    import radar_research
    monkeypatch.setattr(scanner.native,'ensure_indexes',AsyncMock())
    monkeypatch.setattr(radar_research,'context',AsyncMock(return_value={'evidence':[]}))
    monkeypatch.setattr(radar_research,'asset_report',AsyncMock(return_value={'model_state':'timeframe_not_trained'}))
    market=AsyncMock(return_value=quote(planning=True,timeframe='weekly',source_time=(NOW-timedelta(days=2)).isoformat()))
    monkeypatch.setattr(scanner.radar_signals,'market',market)
    chain=AsyncMock();monkeypatch.setattr(scanner.radar_options,'chain',chain)
    result=asyncio.run(scanner.collect('options','AAPL','weekly'))
    assert len(result['plays'])==1
    play=result['plays'][0]
    assert play['direction']=='CALL' and 'option' not in play and 'No contract' in play['option_note']
    chain.assert_not_awaited()
    assert market.call_args.args[1]=='weekly'


@pytest.mark.parametrize('hour,expected',[(15,178.5),(17,179.5)])
def test_stock_daily_provider_excludes_live_session_and_uses_exchange_close(monkeypatch,hour,expected):
    import httpx
    import radar_signals
    from test_radar_opportunities import Store
    from zoneinfo import ZoneInfo
    zone=ZoneInfo('America/New_York')
    today=datetime(2026,11,16,9,30,tzinfo=zone)
    stamp=today.replace(hour=hour).timestamp()
    class Clock:
        @classmethod
        def now(cls,tz):return datetime.fromtimestamp(stamp,tz)
        fromtimestamp=staticmethod(datetime.fromtimestamp)
    monkeypatch.setattr(radar_signals,'datetime',Clock)
    monkeypatch.setattr(radar_signals,'db',SimpleNamespace(kaos_market_signals=Store(),kaos_market_signal_locks=Store()))
    times=[int((today-timedelta(days=79-i)).timestamp()) for i in range(80)]
    data={'timestamp':times,'meta':{'exchangeTimezoneName':'America/New_York','currentTradingPeriod':{'regular':{'end':int(today.replace(hour=16,minute=0).timestamp())}}},
        'indicators':{'quote':[{'low':[99+i for i in range(80)],'high':[101+i for i in range(80)],'open':[100+i for i in range(80)],'close':[100.5+i for i in range(80)],'volume':[100]*80}]}}
    async def get(self,url,**kwargs):
        assert kwargs['params']=={'interval':'1d','range':'1y'}
        return httpx.Response(200,json={'chart':{'result':[data]}},request=httpx.Request('GET',url))
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    result=asyncio.run(radar_signals.market(SimpleNamespace(symbol='AAPL',asset_class='stock'),'monthly'))
    assert result['price']==expected and result['planning'] and result['horizon']=='21 trading sessions'
    assert datetime.fromisoformat(result['source_time']).astimezone(zone).hour==16


def test_any_timeframe_assesses_each_horizon_separately(monkeypatch):
    import radar_opportunities as scanner
    async def collect(market,focus,frame,shared=None):
        plan=setup({'symbol':'AAPL','asset_class':'stock'},quote(planning=frame!='intraday',timeframe=frame),{},NOW)
        return {'plays':[plan],'scanned':1,'universe_size':1,'coverage':[]}
    collector=AsyncMock(side_effect=collect);monkeypatch.setattr(scanner,'collect',collector)
    result=asyncio.run(scanner.collect_any('stocks'))
    assert {p['timeframe'] for p in result['plays']}=={'intraday','daily','weekly','monthly'}
    assert collector.await_count==4 and result['scanned']==4
    assert OpportunityInput(timeframe='any').timeframe=='any'
