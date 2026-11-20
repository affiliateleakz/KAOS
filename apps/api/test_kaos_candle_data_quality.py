from kaos_candle_data_quality import audit_candles, chronological_split

def test_empty():
    assert audit_candles([],60)['usable']==0
    assert len(chronological_split([])['test'])==0
