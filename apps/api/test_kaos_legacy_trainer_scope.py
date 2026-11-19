"""Regression checks for strict legacy AI training scope."""
from kaos_ai_trainer import main

def test_legacy_trainer_rejects_other_expiry():
    assert main({"type":"train_xgboost","targetHorizonMs":15000,"samples":[]})["error"] == "legacy_trainer_requires_30s_horizon"

def test_legacy_trainer_rejects_mixed_sources():
    samples=[{"source":"pocket_option","timeframe":5},{"source":"coinbase","timeframe":5}]
    assert main({"type":"train_xgboost","targetHorizonMs":30000,"samples":samples})["error"] == "mixed_source_or_timeframe"

def test_legacy_trainer_rejects_mixed_timeframes():
    samples=[{"source":"pocket_option","timeframe":5},{"source":"pocket_option","timeframe":15}]
    assert main({"type":"train_xgboost","targetHorizonMs":30000,"samples":samples})["error"] == "mixed_source_or_timeframe"

def test_legacy_trainer_rejects_sample_expiry_mismatch():
    assert main({"type":"train_xgboost","samples":[{"targetHorizonMs":60000}]})["error"] == "sample_horizon_mismatch"
