"""Timing and resampling invariants for the timeframe study."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backtest_all_timeframes import aggregate,settle

def bars(n=30):
    ts=np.arange(n)*60000
    return np.column_stack([ts,100+np.arange(n),102+np.arange(n),99+np.arange(n),101+np.arange(n)])

def test_complete_utc_aggregation():
    a=bars()[1:]
    b=aggregate(a,300,60)
    assert b[0].tolist()==[300000,105,111,104,110]
    assert b[-1,0]==1500000

def test_no_upsampling_or_gap_filling():
    with pytest.raises(ValueError):aggregate(bars(),5,60)
    with pytest.raises(ValueError):aggregate(np.delete(bars(),5,axis=0),300,60)

def test_exact_resolution_and_no_overlap():
    a=bars()
    signals=[[60000,1,30],[120000,1,60],[180000,1,60]]
    rows,unresolved=settle(signals,a,60,60,'source_adaptive',0,(0,9999999))
    assert unresolved==1
    assert rows==[(120000,1),(180000,1)]
    rows,_=settle(signals,a,60,60,'3_candles',0,(0,9999999))
    assert rows==[(60000,1)]

def test_split_crossing_is_purged_and_delay_changes_entry():
    a=bars();signals=[[60000,1,60]]
    assert settle(signals,a,60,60,'1_candle',0,(0,120000))[0]==[]
    assert settle(signals,a,60,60,'1_candle',60,(0,999999))[0]==[(120000,1)]

def test_aggregation_prefix_causal():
    a=bars();early=aggregate(a[:10],300,60)
    a[10:,1:]+=1000
    assert np.array_equal(early,aggregate(a,300,60)[:2])
