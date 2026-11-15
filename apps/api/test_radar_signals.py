from radar_signals import assess


def bars(count=80):
    return [[i*900, 99, 101, 100, 100, 10] for i in range(count)]


def test_wait_without_enough_closed_candles():
    assert assess(bars(20), 20*900)['direction'] == 'WAIT'


def test_breakout_requires_trend_and_closed_bar():
    rows = bars()
    rows[-1] = [79*900, 99, 106, 100, 105, 20]
    result = assess(rows, 80*900)
    assert result['direction'] == 'BUY'
    assert result['reference_stop'] < result['price'] < result['reference_target']
    assert assess(rows, 80*900-1)['direction'] == 'WAIT'


def test_stale_or_gapped_data_cannot_signal():
    rows = bars()
    rows[-1] = [79*900, 99, 106, 100, 105, 20]
    assert assess(rows, 83*900)['direction'] == 'WAIT'
    del rows[-3]
    assert assess(rows, 80*900)['direction'] == 'WAIT'


def test_bot_entries_are_scoped_and_expire(monkeypatch):
    from datetime import datetime, timezone, timedelta
    import radar_signals as module
    now = datetime.now(timezone.utc)
    def row(age, **extra):
        return {'id':str(age),'createdAt':(now-timedelta(seconds=age)).isoformat(),
                'expiration':'30s','direction':'BUY','asset':'EURUSD_otc',**extra}
    class Cursor:
        def sort(self,*args): return self
        async def to_list(self,*args): return [row(5),row(31),row(-10),row(2,simulated=True),row(1,expiration='unknown')]
    class Signals:
        def find(self, query, projection):
            assert query == {'userId':'member-one','state':'SIGNAL_GENERATED'}
            return Cursor()
    class DB:
        signals=Signals()
    monkeypatch.setattr(module,'db',DB())
    import asyncio
    response = asyncio.run(module.bot_signals({'id':'member-one'}))
    assert len(response['signals']) == 1
    assert response['signals'][0]['asset'] == 'EURUSD_otc'
    assert response['execution_enabled'] is False


def test_bearish_breakout_and_flat_market():
    assert assess(bars(),80*900)['direction'] == 'WAIT'
    rows=bars()
    rows[-1]=[79*900,94,101,100,95,20]
    result=assess(rows,80*900)
    assert result['direction']=='SELL'
    assert result['reference_target']<result['price']<result['reference_stop']
