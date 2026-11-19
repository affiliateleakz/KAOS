"""Bounded, read-only adapters. Source failures are not empty mention counts."""
import asyncio
import importlib
import json
import logging
import re
import sys
import time
from math import isfinite
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote,urlsplit
import httpx

RPC_ROOTS=('alchemy.com','infura.io','quiknode.pro','publicnode.com','ankr.com','llamarpc.com','drpc.org')

class _RPCLogRedaction(logging.Filter):
 def filter(self,record):
  # httpx INFO logs include full URLs. RPC providers often put API keys in paths.
  if isinstance(record.args,tuple) and len(record.args)>1 and str(record.msg).startswith('HTTP Request:'):
   parsed=urlsplit(str(record.args[1]));host=(parsed.hostname or '').lower()
   if host in ('www.alphavantage.co','alphavantage.co') or any(host==root or host.endswith('.'+root) for root in RPC_ROOTS):
    marker='redacted-provider-path' if host in ('www.alphavantage.co','alphavantage.co') else 'redacted-rpc-path'
    record.args=(record.args[0],f'{parsed.scheme}://{host}/[{marker}]',*record.args[2:])
  return True

_http_logger=logging.getLogger('httpx')
if not any(type(item).__name__=='_RPCLogRedaction' for item in _http_logger.filters):_http_logger.addFilter(_RPCLogRedaction())

LABELS={'reddit':'Reddit','x':'X','bluesky':'Bluesky','facebook':'Facebook Page','news':'News',
        'market':'Market snapshot','sec':'SEC Form 4','ethereum':'Ethereum large transfers','government':'Congress disclosures'}
class SourceIssue(Exception):
 def __init__(self,state,message):self.state=state;self.message=message

def collector(name):
 packaged=Path(__file__).parent/'_news_collectors'
 directory=packaged if packaged.is_dir() else Path(__file__).resolve().parents[2]/'services/collectors'
 if str(directory) not in sys.path:sys.path.insert(0,str(directory))
 return importlib.import_module(name)

def timestamp(value):
 if isinstance(value,(int,float)) and not isinstance(value,bool):return datetime.fromtimestamp(value,timezone.utc)
 if isinstance(value,str):
  parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
  return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
 raise ValueError('Missing source timestamp')

def observation(asset,source,provider,event,when,text,url,now):
 if not isinstance(url,str) or not url.startswith('https://'):return None
 try:published=timestamp(when)
 except (ValueError,TypeError,OverflowError,OSError):return None
 if published>now or now-published>timedelta(days=7):return None
 return {'asset':asset['symbol'],'asset_class':asset['asset_class'],'source':source,'provider':provider,
         'direction':'neutral','strength':.35,'event_id':provider+':'+str(event)[:130],
         'observed_at':now.isoformat(),'published_at':published.isoformat(),
         'source_url':url[:1900],'summary':str(text)[:1200]}

def relevant(symbol,text):
 return bool(re.search(r'(?<![A-Za-z0-9])\$?'+re.escape(symbol)+r'(?![A-Za-z0-9])',text,re.I))

class Sources:
 def __init__(self,settings,client=None):
  self.settings=settings;self.client=client or httpx.AsyncClient(timeout=httpx.Timeout(6,connect=4),follow_redirects=False)
  self.owns_client=client is None;self.limit=asyncio.Semaphore(4);self.once={};self.sec_gate=asyncio.Lock();self.sec_last=0
 async def close(self):
  for task in self.once.values():
   if not task.done():task.cancel()
  if self.once:await asyncio.gather(*self.once.values(),return_exceptions=True)
  if self.owns_client:await self.client.aclose()
 async def shared(self,key,call):
  if key not in self.once:self.once[key]=asyncio.create_task(call())
  return await asyncio.shield(self.once[key])
 def config(self,provider,required=()):
  settings=self.settings.get(provider,{})
  if not settings.get('enabled',True):raise SourceIssue('disabled','Disabled by the owner')
  if settings.get('configuration_error'):raise SourceIssue('setup_required','The saved credential cannot be decrypted; ask the owner to check the vault')
  if any(not settings.get(k) for k in required):raise SourceIssue('setup_required','API connection credentials are required in Admin → Radar Sources')
  return settings
 async def request(self,method,url,raw=False,**kwargs):
  if urlsplit(url).hostname in ('www.sec.gov','data.sec.gov'):
   async with self.sec_gate:
    await asyncio.sleep(max(0,.2-(time.monotonic()-self.sec_last)));self.sec_last=time.monotonic()
  async with self.limit:
   try:
    async with self.client.stream(method,url,**kwargs) as response:
     if response.status_code in (401,403):raise SourceIssue('access_denied',f'Provider rejected API access (HTTP {response.status_code}); check credentials and plan permissions')
     if response.status_code==429:raise SourceIssue('rate_limited','Provider rate limit reached; try again after the scan cache expires')
     if response.status_code>=400:raise SourceIssue('unavailable',f'Provider returned HTTP {response.status_code}')
     content=bytearray()
     async for chunk in response.aiter_bytes():
      content.extend(chunk)
      if len(content)>6_000_000:raise SourceIssue('unavailable','Provider response exceeded the scan size limit')
    return bytes(content) if raw else json.loads(content)
   except (httpx.HTTPError,ValueError):raise SourceIssue('unavailable','Provider could not return usable data') from None
 async def run(self,provider,asset):
  try:
   if provider in ('sec','government') and asset['asset_class'] not in ('stock','etf'):raise SourceIssue('not_applicable','This disclosure adapter applies to stock/ETF tickers')
   if provider=='ethereum' and (asset['symbol']!='ETH' or asset['asset_class']!='crypto'):raise SourceIssue('not_applicable','Native ETH only; include ETH:crypto to scan this source')
   self.config(provider)
   rows,inspected,scope=await getattr(self,provider)(asset)
   rows=list({row['event_id']:row for row in rows}.values())
   return {'provider':provider,'name':LABELS[provider],'asset':asset['symbol'],'asset_class':asset['asset_class'],
           'state':'collected' if rows else 'no_matches','inspected':inspected,'observations':len(rows),'scope':scope,'records':rows}
  except SourceIssue as error:
   return {'provider':provider,'name':LABELS[provider],'asset':asset['symbol'],'asset_class':asset['asset_class'],
           'state':error.state,'message':error.message,'observations':None,'records':[]}
  except Exception:
   return {'provider':provider,'name':LABELS[provider],'asset':asset['symbol'],'asset_class':asset['asset_class'],
           'state':'unavailable','message':'Source data could not be validated','observations':None,'records':[]}
 async def reddit_token(self,cfg):
  async def token():
   data=await self.request('POST','https://www.reddit.com/api/v1/access_token',auth=(cfg['client_id'],cfg['client_secret']),
                           headers={'User-Agent':cfg['user_agent']},data={'grant_type':'client_credentials'})
   if not data.get('access_token'):raise SourceIssue('access_denied','Reddit did not issue an access token')
   return data['access_token']
  return await self.shared('reddit_token',token)
 async def bluesky_token(self,cfg):
  async def token():
   response=await self.request('POST','https://bsky.social/xrpc/com.atproto.server.createSession',json={'identifier':cfg['identifier'],'password':cfg['app_password']})
   if not response.get('accessJwt'):raise SourceIssue('access_denied','Bluesky did not issue an access token')
   return response['accessJwt']
  return await self.shared('bluesky_token',token)
 async def prepare(self,providers):
  # Authenticate once before fan-out so Reddit does not queue behind lower-priority reads.
  async def warm(provider):
   try:
    if provider=='reddit':await self.reddit_token(self.config(provider,('client_id','client_secret','user_agent')))
    elif provider=='bluesky':
     cfg=self.config(provider)
     if cfg.get('identifier') and cfg.get('app_password'):await self.bluesky_token(cfg)
   except Exception:pass  # Per-symbol results retain auth/validation failures; other feeds still run.
  await asyncio.gather(*(warm(provider) for provider in providers if provider in ('reddit','bluesky')))
 async def reddit(self,asset):
  cfg=self.config('reddit',('client_id','client_secret','user_agent'))
  auth=await self.reddit_token(cfg)
  data=await self.request('GET','https://oauth.reddit.com/search',headers={'Authorization':'Bearer '+auth,'User-Agent':cfg['user_agent']},
                           params={'q':'"'+asset['symbol']+'"','sort':'new','t':'day','limit':25,'raw_json':1})
  children=(data.get('data') or {}).get('children')
  if not isinstance(children,list):raise SourceIssue('unavailable','Reddit search returned an invalid response')
  now=datetime.now(timezone.utc);rows=[]
  for child in children[:25]:
   post=child.get('data') or {};text=str(post.get('title',''))+' '+str(post.get('selftext',''))[:700]
   if not relevant(asset['symbol'],text) or not re.fullmatch(r'[A-Za-z0-9]+',str(post.get('id',''))):continue
   item=observation(asset,'social','reddit',post['id'],post.get('created_utc'),
     'Reddit keyword sample: '+text+' · Public post sample, not total mentions or verified sentiment.',
     'https://www.reddit.com/comments/'+post['id'],now)
   if item:rows.append(item)
  return rows[:12],len(children),'Up to 25 recent public post results; exact symbol/cashtag matching; not all Reddit'
 async def x(self,asset):
  cfg=self.config('x',('bearer_token',))
  data=await self.request('GET','https://api.x.com/2/tweets/search/recent',headers={'Authorization':'Bearer '+cfg['bearer_token']},
    params={'query':'$'+asset['symbol']+' -is:retweet','max_results':10,'tweet.fields':'created_at,author_id'})
  if 'errors' in data and 'data' not in data:raise SourceIssue('access_denied','X search is not available for this API credential or query')
  posts=data.get('data',[])
  if not isinstance(posts,list):raise SourceIssue('unavailable','X search returned an invalid response')
  now=datetime.now(timezone.utc);rows=[]
  for post in posts[:10]:
   if not re.fullmatch(r'\d+',str(post.get('id',''))) or not relevant(asset['symbol'],str(post.get('text',''))):continue
   item=observation(asset,'social','x',post['id'],post.get('created_at'),
     'X cashtag sample: '+str(post.get('text',''))[:800]+' · Recent search sample; reposts excluded, not platform-wide sentiment.',
     'https://x.com/i/web/status/'+post['id'],now)
   if item:rows.append(item)
  return rows,len(posts),'Up to 10 recent cashtag posts; requires X recent-search API access'
 async def bluesky(self,asset):
  cfg=self.config('bluesky');headers={};base='https://public.api.bsky.app'
  if bool(cfg.get('identifier'))!=bool(cfg.get('app_password')):raise SourceIssue('setup_required','Provide both Bluesky handle and app password, or leave both blank for public access')
  if cfg.get('identifier'):
   headers={'Authorization':'Bearer '+await self.bluesky_token(cfg),'atproto-proxy':'did:web:api.bsky.app#bsky_appview'};base='https://bsky.social'
  if not re.fullmatch(r'[A-Z][A-Z0-9]{0,7}',asset['symbol']):raise SourceIssue('not_applicable','Bluesky cashtag sampling requires a ticker without punctuation, up to eight characters')
  data=await self.request('GET',base+'/xrpc/app.bsky.feed.searchPosts',headers=headers,params={'q':'$'+asset['symbol'],'sort':'latest','limit':50})
  posts=data.get('posts')
  if not isinstance(posts,list):raise SourceIssue('unavailable','Bluesky search did not return a post sample')
  module=collector('bluesky_search');now=datetime.now(timezone.utc);summary=module.summarize_search(asset['symbol'],posts,now=now)
  rows=[]
  if summary:
   summary.update(asset_class=asset['asset_class'],provider='bluesky');rows.append(summary)
  for post in posts[:50]:
   record=post.get('record') or {};text=str(record.get('text',''));uri=str(post.get('uri',''))
   if not module.URI.fullmatch(uri) or not relevant(asset['symbol'],text):continue
   handle=(post.get('author') or {}).get('handle','')
   if not re.fullmatch(r'[A-Za-z0-9.:-]{3,255}',str(handle)):continue
   item=observation(asset,'social','bluesky',uri,record.get('createdAt') or post.get('indexedAt'),
       'Bluesky cashtag sample: '+text[:800]+' · Bounded search sample, not total platform activity.',
       'https://bsky.app/profile/'+quote(handle,safe='.-:')+'/post/'+uri.rsplit('/',1)[-1],now)
   if item:rows.append(item)
   if len(rows)>=12:break
  return rows,len(posts[:50]),'Up to 50 search results plus matched-post context; authenticated or public AppView'
 async def facebook(self,asset):
  cfg=self.config('facebook',('page_id','access_token','graph_version'))
  if not re.fullmatch(r'\d{1,40}',cfg['page_id']) or not re.fullmatch(r'v\d{1,2}\.\d{1,2}',cfg['graph_version']):raise SourceIssue('setup_required','Facebook requires a numeric Page ID and a valid Graph API version')
  async def posts():return await self.request('GET',f"https://graph.facebook.com/{cfg['graph_version']}/{cfg['page_id']}/posts",headers={'Authorization':'Bearer '+cfg['access_token']},params={'fields':'id,message,created_time,permalink_url','limit':25})
  data=await self.shared('facebook_page',posts)
  if not isinstance(data.get('data'),list):raise SourceIssue('unavailable','Facebook Page response is not usable')
  now=datetime.now(timezone.utc);rows=[]
  for post in data['data'][:25]:
   if not relevant(asset['symbol'],str(post.get('message',''))):continue
   url=post.get('permalink_url','')
   if urlsplit(url).hostname not in ('facebook.com','www.facebook.com'):continue
   item=observation(asset,'social','facebook',post.get('id'),post.get('created_time'),'Authorized Facebook Page sample: '+str(post.get('message',''))[:850],url,now)
   if item:rows.append(item)
  return rows[:12],len(data['data'][:25]),'Up to 25 posts from the configured authorized Page only'
 async def news(self,asset):
  if self.settings.get('alphavantage',{}).get('enabled',True) and self.settings.get('alphavantage',{}).get('api_key'):
   import alpha_vantage
   from radar_news import normalize
   try:
    items=normalize(await alpha_vantage.news());rows=[];now=datetime.now(timezone.utc)
    for row in items:
     candidates={asset['symbol'],'CRYPTO:'+asset['symbol']}
     if not candidates.intersection(row['tickers']):continue
     item=observation(asset,'news','alphavantage',sha256(row['source_url'].encode()).hexdigest(),row['published_at'],row['title']+' '+row['summary'],row['source_url'],now)
     if item:rows.append(item)
    if rows:return rows,len(items),'Alpha Vantage cached headline sample; local KAOS analysis'
   except SourceIssue:pass
  from routes_opportunity import _yahoo_headlines
  ticker=asset['symbol']+'-USD' if asset['asset_class']=='crypto' else asset['symbol']
  async with self.limit:
   rows=await asyncio.wait_for(_yahoo_headlines(ticker,datetime.now(timezone.utc)),8)
  for row in rows:row.update(asset=asset['symbol'],asset_class=asset['asset_class'],provider='news')
  return rows,len(rows),'Ticker headlines only; no article scraping or full-internet search'
 async def market(self,asset):
  now=datetime.now(timezone.utc)
  if asset['asset_class']=='crypto':
   product=asset['symbol']+'-USD';data=await self.request('GET','https://api.exchange.coinbase.com/products/'+product+'/ticker')
   when=data.get('time');value=data.get('price');url='https://www.coinbase.com/price/'+asset['symbol'].lower()
  elif asset['asset_class'] in ('stock','etf'):
   data=await self.request('GET','https://query1.finance.yahoo.com/v8/finance/chart/'+quote(asset['symbol'],safe=''),params={'range':'1d','interval':'5m'})
   meta=data['chart']['result'][0]['meta'];when=meta.get('regularMarketTime');value=meta.get('regularMarketPrice');url='https://finance.yahoo.com/quote/'+quote(asset['symbol'],safe='')
  else:raise SourceIssue('collector_required','This asset class requires its separately connected market collector')
  try:valid_price=float(value)
  except (ValueError,TypeError):raise SourceIssue('unavailable','Market provider did not supply a valid price') from None
  if not isfinite(valid_price) or valid_price<=0:raise SourceIssue('unavailable','Market provider did not supply a valid price')
  item=observation(asset,'technical','market',asset['symbol']+':'+str(when),when,
       f'Reported market price for {asset["symbol"]}: {str(value)[:40]} USD. Snapshot context, not a forecast or full indicator scan.',url,now)
  return [item] if item else [],1,'One reported price snapshot; actual source time retained'
 async def sec(self,asset):
  cfg=self.config('sec',('user_agent',))
  if asset['asset_class'] not in ('stock','etf'):raise SourceIssue('not_applicable','SEC Form 4 discovery applies to company stock tickers')
  if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',cfg['user_agent']):raise SourceIssue('setup_required','SEC User-Agent must identify the organization and contact email')
  async def companies():return await self.request('GET','https://www.sec.gov/files/company_tickers.json',headers={'User-Agent':cfg['user_agent']})
  table=await self.shared('sec_companies',companies)
  match=next((row for row in table.values() if isinstance(row,dict) and row.get('ticker')==asset['symbol']),None)
  if not match:raise SourceIssue('not_applicable','No matching issuer CIK in the SEC ticker table')
  cik=str(match['cik_str']).zfill(10)
  data=await self.request('GET','https://data.sec.gov/submissions/CIK'+cik+'.json',headers={'User-Agent':cfg['user_agent']})
  module=collector('sec_insider_transactions');now=datetime.now(timezone.utc);rows=[]
  links=module.extract_form4_links(cik,data,now,max_filings=1)
  for accession,published,url in links:
   xml=await self.request('GET',url,raw=True,headers={'User-Agent':cfg['user_agent']})
   rows.extend(module.parse_form4_xml(xml,symbol=asset['symbol'],cik=cik,accession=accession,published=published,source_url=url,now=now))
  for row in rows:row.update(provider='sec',asset_class=asset['asset_class'])
  return rows[:12],len(links),'Latest recent Form 4 primary XML; non-derivative reported P/S only'
 async def ethereum(self,asset):
  cfg=self.config('ethereum',('rpc_url',))
  if asset['symbol']!='ETH' or asset['asset_class']!='crypto':raise SourceIssue('not_applicable','This adapter covers native Ethereum only; include ETH:crypto to scan it')
  parsed=urlsplit(cfg['rpc_url']);host=(parsed.hostname or '').lower()
  roots=RPC_ROOTS
  if parsed.scheme!='https' or parsed.username or parsed.password or not any(host==r or host.endswith('.'+r) for r in roots):raise SourceIssue('setup_required','Use an HTTPS RPC from Alchemy, Infura, QuickNode, PublicNode, Ankr, LlamaRPC or dRPC')
  data=await self.request('POST',cfg['rpc_url'],json={'jsonrpc':'2.0','id':1,'method':'eth_getBlockByNumber','params':['safe',True]})
  if data.get('error') or not isinstance(data.get('result'),dict):raise SourceIssue('unavailable','RPC did not return a safe Ethereum block')
  rows=collector('ethereum_whales').observe_safe_block(data['result'],min_eth=500)
  for row in rows:row['provider']='ethereum'
  return rows[:12],len(data['result'].get('transactions',[])),'One safe block, native ETH value ≥500 ETH; no wallet identity or direction claim'
 async def government(self,asset):
  cfg=self.config('government',('api_key',))
  if asset['asset_class'] not in ('stock','etf'):raise SourceIssue('not_applicable','Congress disclosures apply to stock/ETF tickers')
  data=await self.request('GET','https://api.quiverquant.com/beta/historical/congresstrading/'+quote(asset['symbol'],safe=''),headers={'Authorization':'Bearer '+cfg['api_key']})
  if not isinstance(data,list):raise SourceIssue('unavailable','Congress data returned an invalid response')
  now=datetime.now(timezone.utc);rows=[]
  for post in data[:100]:
   if not isinstance(post,dict) or post.get('Ticker')!=asset['symbol']:continue
   report=post.get('ReportDate');trade=post.get('TransactionDate');name=str(post.get('Representative','Unnamed'))[:100]
   try:
    if timestamp(trade)>timestamp(report):continue
   except (ValueError,TypeError):continue
   text=f'Congressional disclosure: {name}; reported {post.get("Transaction","unspecified")} of {asset["symbol"]}; transaction date {trade}; report date {report}; value range {post.get("Range","not supplied")}. Delayed disclosure, not live order flow. Provider: Quiver.'
   event=sha256(json.dumps({k:post.get(k) for k in ('Ticker','Representative','TransactionDate','ReportDate','Transaction','Range','House')},sort_keys=True,default=str).encode()).hexdigest()[:32]
   item=observation(asset,'politician','government',event,report,text,'https://www.quiverquant.com/congresstrading/',now)
   if item:rows.append(item)
   if len(rows)>=12:break
  return rows,min(len(data),100),'Recent reported Congressional disclosures; provider API permission required'
