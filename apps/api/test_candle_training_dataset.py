from candle_training_dataset import prepare

def bars(n=40, gap=False):
    items=[{"asset_class":"crypto","symbol":"BTC-USD","seconds":60,
            "source":"coinbase_exchange_public_candles","ts":i*60000,
            "close":100+i} for i in range(n)]
    if gap:
        for c in items[20:]:c["ts"]+=60000
    return items

def test_chronological_no_boundary_leakage():
    samples=prepare(bars(),horizon_bars=2)
    assert {s["split"] for s in samples}=={"train","validation","test"}
    assert all(s["target_at"]>s["at"] for s in samples)
    assert all(s["label"]=="UP" for s in samples)
    train=[s for s in samples if s["split"]=="train"]
    val=[s for s in samples if s["split"]=="validation"]
    test=[s for s in samples if s["split"]=="test"]
    assert max(s["target_at"] for s in train)<min(s["at"] for s in val)
    assert max(s["target_at"] for s in val)<min(s["at"] for s in test)

def test_gap_excluded():
    samples=prepare(bars(gap=True))
    assert not any(s["at"]==19*60000 for s in samples)
    assert not any(s["at"]==20*60000 for s in samples)

def test_markets_never_mix():
    b=bars()
    b+=[{**x,"asset_class":"stock","symbol":"SPY","source":"alpaca_iex"} for x in bars()]
    assert {s["symbol"] for s in prepare(b)}=={"BTC-USD","SPY"}
