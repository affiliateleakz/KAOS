import asyncio
import json
from datetime import datetime,timezone,timedelta
import httpx
from radar_sources import Sources

NOW=datetime.now(timezone.utc)
AAPL={'symbol':'AAPL','asset_class':'stock'}
ETH={'symbol':'ETH','asset_class':'crypto'}
BTC={'symbol':'BTC','asset_class':'crypto'}

def exercise(provider,asset,config,handler):
 async def run():
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
   sources=Sources({provider:config},client)
   try:return await sources.run(provider,asset)
   finally:await sources.close()
 return asyncio.run(run())

def test_reddit_uses_oauth_and_returns_only_matching_recent_post_samples():
 calls=[]
 def handler(request):
  calls.append(request)
  if request.url.host=='www.reddit.com':
   assert request.method=='POST';assert request.headers['authorization'].startswith('Basic ')
   return httpx.Response(200,json={'access_token':'fixture-access'})
  assert request.url.host=='oauth.reddit.com';assert request.headers['authorization']=='Bearer fixture-access'
  return httpx.Response(200,json={'data':{'children':[{'data':{'id':'abc1','title':'AAPL earnings','selftext':'Public fixture','created_utc':NOW.timestamp()}},{'data':{'id':'abc2','title':'MSFT earnings','created_utc':NOW.timestamp()}}]}})
 out=exercise('reddit',AAPL,{'client_id':'fixture','client_secret':'fixture','user_agent':'KAOS test'},handler)
 assert out['state']=='collected' and len(out['records'])==1
 assert out['inspected']==2 and out['records'][0]['source']=='social'
 assert out['records'][0]['direction']=='neutral'
 assert 'fixture-access' not in json.dumps(out) and len(calls)==2

def test_missing_social_credentials_do_not_make_requests_or_claim_zero_mentions():
 def handler(request):raise AssertionError('No API request should be made')
 for provider in ('reddit','x','facebook'):
  out=exercise(provider,AAPL,{},handler)
  assert out['state']=='setup_required' and out['observations'] is None

def test_x_rate_limit_is_visible_instead_of_an_empty_success():
 out=exercise('x',AAPL,{'bearer_token':'fixture'},lambda request:httpx.Response(429,json={'error':'rate limit'}))
 assert out['state']=='rate_limited' and out['observations'] is None

def test_x_recent_search_keeps_public_provenance():
 def handler(request):
  assert request.url.host=='api.x.com' and request.url.params['max_results']=='10'
  assert request.url.params['query']=='$AAPL -is:retweet'
  return httpx.Response(200,json={'data':[{'id':'12345','text':'$AAPL public earnings discussion','created_at':NOW.isoformat()}]})
 out=exercise('x',AAPL,{'bearer_token':'fixture'},handler)
 assert out['state']=='collected';assert out['records'][0]['source_url']=='https://x.com/i/web/status/12345'
 assert out['records'][0]['direction']=='neutral'

def test_bluesky_public_denial_does_not_claim_no_mentions():
 out=exercise('bluesky',BTC,{},lambda request:httpx.Response(403,text='Access denied'))
 assert out['state']=='access_denied' and out['observations'] is None

def test_authenticated_bluesky_preserves_crypto_class_and_actual_post_time():
 old=(NOW-timedelta(days=20)).isoformat()
 def handler(request):
  if request.url.path.endswith('createSession'):
   assert json.loads(request.content)['password']=='fixture-app-password'
   return httpx.Response(200,json={'accessJwt':'fixture-access'})
  assert request.url.host=='bsky.social';assert request.headers['authorization']=='Bearer fixture-access'
  return httpx.Response(200,json={'posts':[
   {'uri':'at://did:plc:fixture/app.bsky.feed.post/abc1','author':{'handle':'fixture.bsky.social','did':'did:plc:fixture'},'indexedAt':NOW.isoformat(),'record':{'createdAt':NOW.isoformat(),'text':'$BTC discussion'}},
   {'uri':'at://did:plc:fixture/app.bsky.feed.post/abc2','author':{'handle':'fixture.bsky.social','did':'did:plc:fixture'},'indexedAt':NOW.isoformat(),'record':{'createdAt':old,'text':'$BTC stale post'}}]})
 out=exercise('bluesky',BTC,{'identifier':'fixture.bsky.social','app_password':'fixture-app-password'},handler)
 assert out['state']=='collected';assert all(row['asset_class']=='crypto' for row in out['records'])
 assert not any('abc2' in row['source_url'] for row in out['records'])
 assert 'fixture-app-password' not in json.dumps(out)

def test_facebook_reads_one_authorized_page_for_multiple_assets():
 calls=[]
 async def run():
  def handler(request):
   calls.append(request);assert request.url.host=='graph.facebook.com' and request.url.path=='/v23.0/123/posts'
   return httpx.Response(200,json={'data':[{'id':'post1','message':'AAPL and BTC discussion','created_time':NOW.isoformat(),'permalink_url':'https://www.facebook.com/123/posts/1'}]})
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
   sources=Sources({'facebook':{'page_id':'123','access_token':'fixture','graph_version':'v23.0'}},client)
   try:return await asyncio.gather(sources.run('facebook',AAPL),sources.run('facebook',BTC))
   finally:await sources.close()
 results=asyncio.run(run())
 assert len(calls)==1 and all(row['state']=='collected' for row in results)
 assert all('authorized Page only' in row['scope'] for row in results)

def test_native_eth_scan_only_calls_read_only_safe_block_and_never_labels_ownership():
 def handler(request):
  payload=json.loads(request.content);assert payload['method']=='eth_getBlockByNumber' and payload['params']==['safe',True]
  return httpx.Response(200,json={'result':{'number':'0x100','timestamp':hex(int(NOW.timestamp())-30),'transactions':[{'hash':'0x'+'a'*64,'value':hex(600*10**18)}]}})
 out=exercise('ethereum',ETH,{'rpc_url':'https://ethereum-rpc.publicnode.com'},handler)
 assert out['state']=='collected' and out['records'][0]['source']=='onchain'
 assert 'does NOT identify a whale owner' in out['records'][0]['summary']
 assert out['records'][0]['direction']=='neutral'

def test_rpc_configuration_cannot_target_private_or_arbitrary_hosts():
 out=exercise('ethereum',ETH,{'rpc_url':'https://127.0.0.1/secrets'},lambda request:(_ for _ in ()).throw(AssertionError('Unexpected request')))
 assert out['state']=='setup_required'

def test_congress_report_retains_disclosure_and_transaction_dates_and_stable_identity():
 record={'Representative':'Fixture Member','Ticker':'AAPL','Transaction':'Purchase','TransactionDate':(NOW-timedelta(days=20)).date().isoformat(),'ReportDate':NOW.date().isoformat(),'Range':'$1,001 - $15,000','PriceChange':1}
 first=exercise('government',AAPL,{'api_key':'fixture'},lambda request:httpx.Response(200,json=[record]))
 record['PriceChange']=20
 second=exercise('government',AAPL,{'api_key':'fixture'},lambda request:httpx.Response(200,json=[record]))
 assert first['state']=='collected'
 assert first['records'][0]['event_id']==second['records'][0]['event_id']
 assert record['TransactionDate'] in first['records'][0]['summary'] and record['ReportDate'] in first['records'][0]['summary']
 assert first['records'][0]['source']=='politician' and first['records'][0]['direction']=='neutral'


def test_sec_adapter_resolves_issuer_and_parses_actual_purchase_xml():
    accepted=(NOW-timedelta(hours=1)).isoformat()
    transaction=(NOW-timedelta(days=1)).date().isoformat()
    xml=f'''<ownershipDocument><reportingOwner><reportingOwnerId><rptOwnerName>Fixture Officer</rptOwnerName></reportingOwnerId></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>{transaction}</value></transactionDate><transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>100</value></transactionShares><transactionPricePerShare><value>20</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'''
    def handler(request):
        assert 'contact@example.org' in request.headers['user-agent']
        if request.url.path.endswith('company_tickers.json'):
            return httpx.Response(200,json={'0':{'ticker':'AAPL','cik_str':320193}})
        if request.url.host=='data.sec.gov':
            return httpx.Response(200,json={'filings':{'recent':{'form':['4'],'accessionNumber':['0000320193-26-000001'],'primaryDocument':['ownership.xml'],'filingDate':[NOW.date().isoformat()],'acceptanceDateTime':[accepted]}}})
        assert request.url.path.endswith('/ownership.xml')
        return httpx.Response(200,content=xml.encode())
    out=exercise('sec',AAPL,{'user_agent':'KAOS contact@example.org'},handler)
    assert out['state']=='collected' and out['observations']==1
    assert out['records'][0]['source']=='insider'
    assert 'Fixture Officer purchase' in out['records'][0]['summary']
    assert transaction in out['records'][0]['summary']
    assert out['records'][0]['direction']=='neutral'


def test_rpc_credentials_in_url_never_appear_in_httpx_info_logs(caplog):
    import logging
    caplog.set_level(logging.INFO,logger='httpx')
    block={'number':'0x100','timestamp':hex(int(NOW.timestamp())-30),'transactions':[]}
    result=exercise('ethereum',ETH,{'rpc_url':'https://eth-mainnet.g.alchemy.com/v2/private-rpc-fixture-token'},lambda request:httpx.Response(200,json={'result':block}))
    assert result['state']=='no_matches'
    assert 'private-rpc-fixture-token' not in caplog.text
    assert '[redacted-rpc-path]' in caplog.text


def test_social_auth_is_prepared_once_and_malformed_auth_does_not_stop_other_sources():
    async def run():
        calls=[]
        def handler(request):
            calls.append(request)
            if request.url.host=='www.reddit.com':return httpx.Response(200,json=[])
            return httpx.Response(200,json={'data':[]})
        config={'reddit':{'client_id':'fixture','client_secret':'fixture','user_agent':'KAOS tests'},'x':{'bearer_token':'fixture'}}
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sources=Sources(config,client)
            try:
                await sources.prepare(['reddit','x'])
                results=await asyncio.gather(sources.run('reddit',AAPL),sources.run('x',AAPL))
                assert results[0]['state']=='unavailable' and results[0]['observations'] is None
                assert results[1]['state']=='no_matches'
                assert sum(request.url.host=='www.reddit.com' for request in calls)==1
            finally:await sources.close()
    asyncio.run(run())
