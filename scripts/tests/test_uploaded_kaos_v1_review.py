"""Regression arithmetic for the package audit; no external code/data required."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import review_uploaded_kaos_v1 as r

def test_mixed_wins_and_losses_produce_non_degenerate_interval():
    lo,hi=r.correct_wr_interval(['tp','sl']*10)
    assert 0<lo<.5<hi<1

def test_unreviewed_package_is_not_executed(tmp_path):
    (tmp_path/'strategy.py').write_text("raise RuntimeError('must not execute')")
    with pytest.raises(ValueError,match='Unreviewed calculation'):r.pure_modules(tmp_path)

def test_round_trip_cost_is_adverse_for_both_directions():
    for side in [-1,1]:
        assert r.price_cost_pnl(side,100,100,1,.001,.0002)==pytest.approx(-.24)
        assert r.price_cost_pnl(side,100,100,1,.002,.0004)==pytest.approx(-.48)

def test_cost_stress_reduces_gross_winners_in_either_direction():
    for side,exit in [(1,105),(-1,95)]:
        assert r.price_cost_pnl(side,100,exit,1,.002,.0004)<r.price_cost_pnl(side,100,exit,1,.001,.0002)<5
