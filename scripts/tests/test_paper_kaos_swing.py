"""Offline paper journal checks. Fixtures are not forward market evidence."""
import sys,json
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import paper_kaos_swing as p

def observation():
    rows=np.column_stack((np.arange(1200)*p.HOUR,np.full(1200,100.),np.full(1200,103.),np.full(1200,97.),np.full(1200,100.)))
    return {'symbol':'BTCUSDT','observedAt':1200*p.HOUR+1000,'bid':100.,'ask':100.1,'bars':rows.tolist(),'source':'offline unit fixture'}

@pytest.fixture
def conn(tmp_path):
    c=p.database(tmp_path/'paper.sqlite')
    yield c
    c.close()

@pytest.fixture
def force_setup(monkeypatch):monkeypatch.setattr(p.rules.prior,'spot_signals',lambda f,family:np.ones(len(f),dtype=bool))

def test_retry_cannot_duplicate_entry(conn,force_setup):
    obs=observation();r=p.process(conn,obs,now=obs['observedAt']);assert [e['kind'] for e in r['events']].count('PAPER_ENTRY')==1
    assert p.process(conn,obs,now=obs['observedAt'])['duplicate']
    assert conn.execute("SELECT count(*) FROM events WHERE kind='PAPER_ENTRY'").fetchone()[0]==1
    assert all(e['executionEnabled'] is False and e['brokerOrderSubmitted'] is False for e in r['events'])

def test_replay_cannot_enter_forward_journal(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True)
    obs['observedAt']+=1000
    with pytest.raises(ValueError,match='mode mismatch'):p.process(conn,obs,now=obs['observedAt'])
    assert p.status(conn)['identity']['mode']=='replay'


def test_stale_quote_and_forming_candles_rejected(conn):
    obs=observation()
    with pytest.raises(ValueError,match='Stale or future quote'):p.process(conn,obs,now=obs['observedAt']+30001)
    obs['bars'][-1][0]+=p.HOUR
    with pytest.raises(ValueError,match='forming'):p.process(conn,obs,now=obs['observedAt'])
    assert p.status(conn)['observations']==0


def test_conflicting_candle_rolls_back_entire_observation(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True);before=p.status(conn);obs['observedAt']+=1000;obs['bars'][-1][4]=101
    with pytest.raises(ValueError,match='Conflicting immutable'):p.process(conn,obs,replay=True)
    assert p.status(conn)==before


def test_missed_entry_is_not_backfilled(conn,force_setup):
    obs=observation();obs['observedAt']+=180000
    r=p.process(conn,obs,replay=True)
    assert not r['openPosition'];assert any(e.get('reason')=='missed_entry_window' for e in r['events'])


def test_real_quote_side_and_stop_fill_are_used(conn,force_setup):
    obs=observation();first=p.process(conn,obs,replay=True);entry=next(e for e in first['events'] if e['kind']=='PAPER_ENTRY')
    assert entry['entryFill']==pytest.approx(obs['ask']*1.0002)
    obs['observedAt']+=60000;obs['bid']=80.;obs['ask']=80.1
    r=p.process(conn,obs,replay=True);exit=next(e for e in r['events'] if e['kind']=='PAPER_EXIT')
    assert exit['exitFill']==pytest.approx(80*.9998) and exit['reason']=='observed_stop_quote'
    assert not r['openPosition'] and p.status(conn)['closedPaperTrades']==1


def test_gap_is_recorded_and_current_quote_used(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True);obs['observedAt']+=180000;obs['bid']=75.;obs['ask']=75.1
    r=p.process(conn,obs,replay=True)
    assert any(e['kind']=='COVERAGE_GAP' for e in r['events'])
    exit=next(e for e in r['events'] if e['kind']=='PAPER_EXIT')
    assert exit['exitFill']==pytest.approx(75*.9998) and exit['executionCoverageIncomplete']
    assert p.status(conn)['closedTradesWithCoverageIssues']==1


def test_insufficient_or_gapped_context_holds(conn,force_setup):
    obs=observation();obs['bars']=obs['bars'][-100:]
    r=p.process(conn,obs,replay=True)
    assert not r['openPosition'] and any(e.get('reason')=='insufficient_contiguous_history' for e in r['events'])


def test_no_reentry_on_exit_observation(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True);obs['observedAt']+=60000;obs['bid']=80.;obs['ask']=80.1
    r=p.process(conn,obs,replay=True)
    assert any(e['kind']=='PAPER_EXIT' for e in r['events'])
    assert not any(e['kind']=='PAPER_ENTRY' for e in r['events'])


def test_bad_quotes_and_future_clock_rejected(conn):
    obs=observation();obs['bid']=obs['ask']+1
    with pytest.raises(ValueError,match='Invalid bid'):p.process(conn,obs,replay=True)
    obs=observation()
    with pytest.raises(ValueError,match='future quote'):p.process(conn,obs,now=obs['observedAt']-5001)


def test_out_of_order_new_observation_rejected(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True);obs['bid']=99.
    with pytest.raises(ValueError,match='Out-of-order'):p.process(conn,obs,replay=True)


def test_journal_pins_engine_fingerprint(conn,force_setup,monkeypatch):
    obs=observation();p.process(conn,obs,replay=True);obs['observedAt']+=60000;monkeypatch.setattr(p,'fingerprint',lambda:'different-engine')
    with pytest.raises(ValueError,match='Engine/config'):p.process(conn,obs,replay=True)


def test_public_adapter_uses_only_read_endpoints_and_excludes_empty_bars(monkeypatch):
    calls=[]
    class Response:
        def __init__(self,data):self.data=data
        def raise_for_status(self):pass
        def json(self):return self.data
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,path,params):
            calls.append(path)
            if path.endswith('bookTicker'):return Response({'bidPrice':'100','askPrice':'101'})
            return Response([[0,'100','101','99','100',0,0,0,1],[p.HOUR,'100','101','99','100',0,0,0,0]])
    monkeypatch.setattr(p.httpx,'Client',Client);monkeypatch.setattr(p.time,'time',lambda:3*p.HOUR/1000)
    obs=p.public_snapshot('BTCUSDT',bootstrap=False)
    assert len(obs['bars'])==1 and obs['bars'][0][0]==0
    assert set(calls)=={'/api/v3/klines','/api/v3/ticker/bookTicker'}
    assert obs['bid']==100 and obs['ask']==101


def test_feed_failure_never_inserts_an_observation(tmp_path,monkeypatch):
    path=tmp_path/'failed.sqlite'
    def failure(*args,**kwargs):raise p.httpx.ConnectError('public feed unavailable')
    monkeypatch.setattr(p,'coinbase_snapshot',failure)
    monkeypatch.setattr(sys,'argv',['paper_kaos_swing','--database',str(path),'--symbol','BTCUSDT'])
    with pytest.raises(SystemExit) as result:p.main()
    assert json.loads(str(result.value))['observationNotCommitted']
    c=p.database(path)
    try:assert p.status(c)['observations']==0
    finally:c.close()


def test_feed_and_fee_settings_cannot_be_mixed(conn,force_setup):
    obs=observation();p.process(conn,obs,replay=True,fee_bps=60);obs['observedAt']+=1000
    with pytest.raises(ValueError,match='mismatch'):p.process(conn,obs,replay=True,fee_bps=10)
    obs['feed']='different_feed'
    with pytest.raises(ValueError,match='mismatch'):p.process(conn,obs,replay=True,fee_bps=60)


def test_coinbase_adapter_reorders_ohlc_and_excludes_forming_candle(monkeypatch):
    calls=[];now=1000*p.HOUR
    class Response:
        def __init__(self,data):self.data=data
        def raise_for_status(self):pass
        def json(self):return self.data
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,path,params=None):
            calls.append(path)
            if path.endswith('ticker'):return Response({'bid':'100','ask':'101'})
            return Response([[now//1000,99,104,101,103,2],[(now-p.HOUR)//1000,98,103,100,102,2]])
    monkeypatch.setattr(p.httpx,'Client',Client);monkeypatch.setattr(p.time,'time',lambda:now/1000+1)
    obs=p.coinbase_snapshot('BTCUSDT',False)
    assert obs['product']=='BTC-USD' and obs['feed']=='coinbase_public'
    assert obs['bars']==[[now-p.HOUR,100.,103.,98.,102.]]
    assert set(calls)=={'/products/BTC-USD/candles','/products/BTC-USD/ticker'}


def test_coinbase_explicitly_rejects_unmapped_bnb():
    with pytest.raises(ValueError,match='supported Coinbase'):p.coinbase_snapshot('BNBUSDT')


def test_fee_inputs_reject_nan(conn):
    obs=observation()
    with pytest.raises(ValueError,match='finite'):p.process(conn,obs,replay=True,fee_bps=float('nan'))
