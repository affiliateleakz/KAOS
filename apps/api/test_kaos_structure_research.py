from kaos_structure_research import signal
def bar(i,o,h,l,c):
    return {"ts":i*15000,"open":o,"high":h,"low":l,"close":c}
def baseline():
    return [bar(i,100,101,99,100) for i in range(16)]
def test_flat_no_signal():
    assert signal(baseline()) is None
def test_call_breakout():
    b=baseline();b[-1]=bar(15,100,104,100,103)
    result=signal(b)
    assert result["setup"]=="BREAKOUT" and result["direction"]=="CALL"
def test_put_breakout():
    b=baseline();b[-1]=bar(15,100,100,96,97)
    result=signal(b)
    assert result["setup"]=="BREAKOUT" and result["direction"]=="PUT"
def test_no_short_history():
    assert signal(baseline()[:8]) is None
