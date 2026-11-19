"""CCI formula and closed-candle reversal rules read from supplied bundle."""
import importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
SCRIPT_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPT_DIR))
import backtest_uploaded_bundle as bundle


def test_cci_uses_observed_ohlc4_and_point02_divisor():
    a=np.array([[i*5000,100+i,103+i,99+i,102+i] for i in range(25)],float)
    p=(a[:,1]+a[:,2]+a[:,3]+a[:,4])/4;window=p[-20:];expected=(p[-1]-window.mean())/(.02*np.abs(window-window.mean()).mean())
    assert bundle.cci_values(a)[-1]==pytest.approx(expected)
    assert np.array_equal(bundle.cci_values(a[:23]),bundle.cci_values(a)[:23],equal_nan=True)


def test_four_candles_fades_closed_colors_and_doji_breaks_setup():
    a=np.array([[i*5000,100,102,99,101] for i in range(305)],float)
    signals=bundle.signals(a,'bundle_four_candles','source');assert signals[300]==-1
    a[299,4]=100
    assert bundle.signals(a,'bundle_four_candles','source')[300]==0
