import pytest
import kaos_trend_pause as strategy

def make_candle(ts, price):
    return {"ts":ts,"open":price-0.03,"high":price+0.08,"low":price-0.08,"close":price}

def test_ema_warmup_and_constant_price():
    assert strategy.ema([1]*19,20) is None
    assert strategy.ema([10]*25,20)[-1] == 10

def test_invalid_input_rejected_without_trading():
    with pytest.raises(ValueError):
        strategy.validate([{"ts":1,"open":1,"high":2,"low":0.5,"close":1},
                           {"ts":1,"open":1,"high":2,"low":0.5,"close":1}])
    with pytest.raises(ValueError):
        strategy.validate([{"ts":1,"open":float("nan"),"high":2,"low":0.5,"close":1}])

def test_no_signal_on_incomplete_one_minute_candle():
    # Last 1m candle is still open when final 15s candle closes; test must not peek.
    minute=[make_candle(i*60000,100+i*.1) for i in range(53)]
    fast=[make_candle(i*15000,101+i*.01) for i in range(24)]
    assert strategy.signal(minute,fast) is None

def test_no_signal_on_flat_or_short_history():
    minute=[make_candle(i*60000,100) for i in range(80)]
    fast=[make_candle((i+300)*15000,100) for i in range(40)]
    assert strategy.signal(minute,fast) is None
    assert strategy.signal(minute[:30],fast) is None

def test_signal_result_never_authorizes_live_trading():
    minute=[make_candle(i*60000,100+i*.1) for i in range(80)]
    # 15s candles closely aligned to completed 1m history, 1 red pause and breakout.
    fast=[make_candle((i+280)*15000,107+i*.005) for i in range(39)]
    fast[-2]={"ts":fast[-2]["ts"],"open":108.7,"high":108.75,"low":108.5,"close":108.6}
    fast[-1]={"ts":fast[-1]["ts"],"open":108.6,"high":109.05,"low":108.58,"close":109.0}
    result=strategy.signal(minute,fast)
    assert result is None or (result["direction"]=="CALL" and result["trade_executable"] is False)
