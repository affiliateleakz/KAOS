// Real Radar and admin UI, mocked sources only. No live providers, paid calls or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext();let scanCalls=0,latest=null,vaultReady=false,savedKey=null,sourceQueries=[],lastMarketAssets=null,socialCalls=0,opportunityCalls=0,lastOpportunity=null;
 const labels={alphavantage:'Alpha Vantage',reddit:'Reddit',x:'X',bluesky:'Bluesky',facebook:'Facebook Pages',sec:'SEC insider transactions',ethereum:'Ethereum large transfers',government:'Congressional disclosures'};
 const fields={alphavantage:[['api_key','API key']],reddit:[['client_id','Client ID'],['client_secret','Client secret'],['user_agent','Identifying User-Agent']],x:[['bearer_token','API bearer token']],bluesky:[['identifier','Account handle'],['app_password','App password']],facebook:[['page_id','Authorized Page ID']],sec:[['user_agent','Organization and contact email']],ethereum:[['rpc_url','HTTPS RPC URL']],government:[['api_key','Quiver API key']]};
 const providers=()=>Object.entries(labels).map(([id,name])=>({id,name,enabled:true,description:'Fixture provider setup; no live request',configured:['reddit','bluesky'].includes(id)||id==='x'&&!!savedKey,fields:fields[id].map(([name,label])=>({name,label,configured:false,secret:['bearer_token','api_key','app_password','client_secret'].includes(name)}))}));
 const report=()=>({completed_at:'2026-11-15T12:00:00Z',coverage:'Selected public evidence samples',cached:false,
  source_status:[{provider:'reddit',asset:'AAPL',state:'collected',observations:1,inspected:25,scope:'25 public post results'},{provider:'x',asset:'AAPL',state:'access_denied',observations:null,message:'Provider rejected API access; check API permissions'},{provider:'ethereum',asset:'ETH',state:'collected',observations:1,inspected:150,scope:'One safe block, native ETH only'},{provider:'government',asset:'AAPL',state:'no_matches',observations:0,inspected:3,scope:'Recent disclosed Congress transactions'}],
  evidence:[{id:'reddit-ref',asset:'AAPL',asset_class:'stock',provider:'reddit',source:'social',summary:'Public Reddit AAPL discussion fixture.',source_url:'https://www.reddit.com/comments/fixture',published_at:'2026-11-15T11:00:00Z',observed_at:'2026-11-15T12:00:00Z'},{id:'eth-ref',asset:'ETH',asset_class:'crypto',provider:'ethereum',source:'onchain',summary:'Native ETH large-value transaction fixture; owner and direction unknown.',source_url:'https://etherscan.io/tx/fixture',published_at:'2026-11-15T11:00:00Z',observed_at:'2026-11-15T12:00:00Z'}],
  ai:{state:'complete',model:'fixture-model',observations_reviewed:2,report:{summary:'AI research fixture: public evidence requires source verification.',assets:[{symbol:'AAPL',asset_class:'stock',priority:'medium',explanation:'One public discussion source; no confirmed market direction.',evidence_ids:['reddit-ref'],limitations:['X could not be collected.']},{symbol:'ETH',asset_class:'crypto',priority:'low',explanation:'A native transfer does not identify a buyer.',evidence_ids:['eth-ref'],limitations:['One safe block only.']}],coverage_gaps:['X API access is unavailable.']}}});
 await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await context.route('**/api/**',route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname;
  if(path==='/api/auth/me')return route.fulfill({json:{id:'owner',role:'super_admin',name:'Owner'}});
  if(path==='/api/notifications')return route.fulfill({json:[]});
  if(path==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{tier:'ultimate',scanners:true}}});
  if(path==='/api/v1/intelligence/opportunities'){sourceQueries.push(url.searchParams.get('source_filter'));return route.fulfill({json:{results:[],scanned_observations:0}});}
  if(path==='/api/v1/intelligence/signals/opportunities'){opportunityCalls++;lastOpportunity=req.postDataJSON();const symbol=lastOpportunity.symbol||(lastOpportunity.market==='forex'?'EURUSD':lastOpportunity.market==='crypto'?'BTC':'AAPL');return route.fulfill({json:{state:'complete',market:lastOpportunity.market,plays:lastOpportunity.market==='options'?[]:[{symbol,direction:'BUY',score:80,basis:'KAOS technical setup; AI not confirming',model_state:'collecting',reason:'Trend and momentum agree.',reference_entry:100,reference_stop:97,reference_target:106,reward_risk:2,horizon:'45–60 minutes',score_components:{trend:25},source:'Fixture candles',source_time:new Date().toISOString(),expires_at:new Date(Date.now()+300000).toISOString()}],scanned:12,universe_size:12,coverage:lastOpportunity.market==='options'?['Options require OPRA.']:[],message:lastOpportunity.market==='options'?'Options need OPRA chain access.':null,execution_enabled:false}});}
  if(path==='/api/v1/intelligence/signals/market'){lastMarketAssets=req.postDataJSON().assets;return route.fulfill({json:{signals:[{symbol:'BTC',asset_class:'crypto',direction:'WAIT',reason:'No confirmed trend breakout.',model_state:'collecting',source:'KAOS local fixture',feature_values:{return_1:.01,return_4:.02,volume_ratio:1.5},sentiment:{sources:{news:{samples:1,score:.5,bullish:1,bearish:0,neutral:0},social:{samples:0,score:null,bullish:0,bearish:0,neutral:0}}}}],ai_status:'KAOS local model collecting evidence'}});}
  if(path==='/api/v1/intelligence/sentiment/history')return route.fulfill({json:{history:[{observed_at:'2026-11-15T12:00:00Z',sentiment:{sources:{news:{score:.5},social:{score:null}}}}]}});
  if(path==='/api/v1/intelligence/trending/stocks')return route.fulfill({json:{state:'complete',provider:'ApeWisdom',rankings:[{symbol:'AAPL',name:'Apple',mentions:42,rank:1,previous_mentions:30,mention_change:12,upvotes:100}],fetched_at:'2026-11-15T12:00:00Z',stale:false}});
  if(path==='/api/v1/intelligence/social/mentions')throw Error('Retired social scanner must never be called');
  if(path==='/api/v1/intelligence/signals/bot')return route.fulfill({json:{signals:[]}});
  if(path==='/api/v1/intelligence/news/feed')return route.fulfill({json:{state:'complete',articles:[{title:'Market headline fixture',summary:'Latest stock news',source:'Alpha Vantage',source_url:'https://example.com/news',published_at:'2026-11-15T12:00:00Z',tickers:['AAPL']}]}});
  if(path==='/api/v1/intelligence/scan/status')return route.fulfill({json:{providers:providers(),maximum_assets:5,cache_seconds:300}});
  if(path==='/api/v1/intelligence/scan/latest')return route.fulfill({json:{scan:latest}});
  if(path==='/api/v1/intelligence/scan'){
   scanCalls++;const data=req.postDataJSON();assert.deepEqual(data.assets,[{symbol:'AAPL',asset_class:'stock'},{symbol:'ETH',asset_class:'crypto'}]);assert.equal(data.include_ai,true);latest=report();return route.fulfill({json:latest});
  }
  if(path==='/api/admin/radar/model/train')return route.fulfill({json:{state:'collecting'}});
  if(path==='/api/admin/radar/model')return route.fulfill({json:{engine:'KAOS local',groups:[{group:'crypto',labeled_samples:0,active:null,candidate:null}]}});
  if(path==='/api/admin/radar/providers')return route.fulfill({json:{providers:providers(),vaultReady}});
  if(path==='/api/admin/radar/vault/initialize'){vaultReady=true;return route.fulfill({json:{vaultReady:true}});}
  if(path==='/api/admin/radar/providers/alphavantage'){savedKey=req.postDataJSON().credentials.api_key;return route.fulfill({json:{id:'alphavantage',configured:true}});}
  return route.fulfill({status:404,json:{detail:'No fixture'}});
 });
 const page=await context.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.clock.install();
 await page.goto(BASE+'/dashboard/opportunities');await page.getByRole('heading',{name:'KAOS Radar',exact:true}).waitFor();
 const nav=page.getByRole('navigation',{name:'Radar sections'});
 assert.deepEqual(await nav.getByRole('button').allTextContents(),['News','Trending','AI Signal','Sentiment','Bot Entries']);
 await page.getByRole('heading',{name:'Market headline fixture',exact:true}).waitFor();
 assert.equal(await page.getByLabel('Signal ticker',{exact:true}).count(),0,'News must not include unrelated AI controls');
 await nav.getByRole('button',{name:'Trending',exact:true}).click();
 await page.getByRole('cell',{name:'42',exact:true}).waitFor();
 await page.getByText('No API key needed.',{exact:false}).waitFor();
 await page.getByRole('link',{name:'Source: ApeWisdom ↗',exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.getByRole('button',{name:'Analyze AAPL with KAOS',exact:true}).click();
 await page.getByRole('heading',{name:'1. AAPL · BUY',exact:true}).waitFor();
 assert.equal(lastOpportunity.symbol,'AAPL');assert.equal(lastOpportunity.market,'stocks');
 assert.equal(await page.getByRole('heading',{name:'Market Sentiment Monitoring',exact:true}).count(),0);
 assert.equal(await page.getByText('Model: collecting.',{exact:false}).isVisible(),false,'Model details remain collapsed');
 await page.getByText('Why this play?',{exact:true}).click();await page.getByText('Model: collecting.',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Scan the market',exact:true}).click();
 await page.getByLabel('Opportunity market',{exact:true}).selectOption('crypto');
 await page.getByRole('heading',{name:'1. BTC · BUY',exact:true}).waitFor();
 const countChange=page.waitForResponse(r=>r.url().endsWith('/api/v1/intelligence/signals/opportunities')&&r.request().postDataJSON().limit===10);
 await page.getByLabel('Number of plays',{exact:true}).selectOption('10');await countChange;
 await page.getByRole('heading',{name:'1. BTC · BUY',exact:true}).waitFor();assert.equal(lastOpportunity.limit,10);
 await page.getByLabel('Opportunity market',{exact:true}).selectOption('forex');
 await page.getByRole('heading',{name:'1. EURUSD · BUY',exact:true}).waitFor();
 await page.getByLabel('Opportunity market',{exact:true}).selectOption('options');
 await page.getByText('Options need OPRA chain access.',{exact:true}).waitFor();
 assert.equal(await page.getByRole('heading',{name:/^1\./}).count(),0,'No fabricated options plays');
 await nav.getByRole('button',{name:'Sentiment',exact:true}).click();
 await page.getByRole('heading',{name:'Market Sentiment Monitoring',exact:true}).waitFor();
 await page.getByRole('button',{name:'Check sentiment',exact:true}).click();
 await page.getByText('Bullish 1 · Neutral 0 · Bearish 0',{exact:true}).waitFor();
 await nav.getByRole('button',{name:'Bot Entries',exact:true}).click();
 await page.getByRole('button',{name:'Refresh entries',exact:true}).click();
 await page.getByText('No fresh bot entries.',{exact:true}).waitFor();
 assert.equal(scanCalls,0,'Simple member views must not mount the old evidence workspace');
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 if(process.env.KAOS_CAPTURE_DIR)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/radar-simple.png'});
 await page.setViewportSize({width:1440,height:1000});
 await page.goto(BASE+'/admin/radar');await page.getByTestId('radar-source-settings').waitFor();
 assert.ok(!(await page.locator('body').innerText()).includes('OpenAI API key'));
 await page.getByRole('button',{name:'Train crypto model',exact:true}).click();
 await page.getByRole('status').filter({hasText:'KAOS model: collecting'}).waitFor();
 const count=opportunityCalls;await page.clock.fastForward(300010);assert.equal(opportunityCalls,count,'Opportunity polling stops after leaving Radar');
 await page.getByRole('button',{name:'Initialize private vault',exact:true}).click();await page.getByRole('button',{name:'Verify private vault',exact:true}).waitFor();
 assert.equal(await page.getByLabel('X API bearer token',{exact:true}).count(),0);
 const input=page.getByLabel('Alpha Vantage API key',{exact:true});await input.fill('fixture-private-alpha-token');
 await page.getByRole('button',{name:'Save Alpha Vantage',exact:true}).click();await page.getByRole('status').filter({hasText:'Alpha Vantage settings saved'}).waitFor();
 assert.equal(savedKey,'fixture-private-alpha-token');assert.equal(await input.inputValue(),'');assert.ok(!(await page.locator('body').innerText()).includes('fixture-private-alpha-token'));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('Simple Radar: five top tabs, news default, isolated views, keyless trending-to-scanner flow, four markets, play count and unavailable-options honesty, collapsed model details, mobile layout and owner settings passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
