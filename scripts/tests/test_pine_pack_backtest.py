"""Backtest fill assumptions: no network, broker credentials or real orders."""
import importlib.util
from pathlib import Path
import pandas as pd
import pytest
spec=importlib.util.spec_from_file_location('pine_backtest',Path(__file__).resolve().parents[1]/'backtest_pine_pack.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)


def fixture(second=None):
    rows=[]
    for i in range(3):
        row={'ts':i*3600000,'open':100.,'high':101.,'low':99.,'close':100.,'atr':1.,'entry_trend':i==0,'exit_trend':False}
        if i==1 and second:row.update(second)
        rows.append(row)
    return pd.DataFrame(rows)


def test_signal_fills_next_open_not_signal_close():
    _,trades=engine.simulate(fixture(), 'trend','stocks',0,4*3600000)
    assert trades[0]['entry_ts']==3600000
    assert trades[0]['entry']==pytest.approx(100*1.0002)


def test_both_brackets_touch_uses_stop_first():
    _,trades=engine.simulate(fixture({'high':110.,'low':90.}), 'trend','stocks',0,4*3600000)
    assert trades[0]['reason']=='stop'
    assert trades[0]['exit']==pytest.approx((100*1.0002-2)*.9998)


def test_retail_crypto_costs_reduce_equity_and_stress_costs_more():
    normal,_=engine.simulate(fixture(),'trend','crypto',0,4*3600000)
    stress,_=engine.simulate(fixture(),'trend','crypto',0,4*3600000,stress=2)
    assert stress['final_equity']<normal['final_equity']<10000


def test_period_starts_flat_and_does_not_fill_earlier_signal():
    summary,trades=engine.simulate(fixture(),'trend','crypto',3600000,4*3600000)
    assert not trades and summary['final_equity']==10000
