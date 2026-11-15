// Real Radar and admin UI, mocked sources only. No live providers, paid calls or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext();let scanCalls=0,latest=null,vaultReady=false,savedKey=null,sourceQueries=[];
 const labels={reddit:'Reddit',x:'X',bluesky:'Bluesky',facebook:'Facebook Pages',sec:'SEC insider transactions',ethereum:'Ethereum large transfers',government:'Congressional disclosures',openai:'Radar AI analysis'};
 const fields={reddit:[['client_id','Client ID'],['client_secret','Client secret'],['user_agent','Identifying User-Agent']],x:[['bearer_token','API bearer token']],bluesky:[['identifier','Account handle'],['app_password','App password']],facebook:[['page_id','Authorized Page ID']],sec:[['user_agent','Organization and contact email']],ethereum:[['rpc_url','HTTPS RPC URL']],government:[['api_key','Quiver API key']],openai:[['api_key','OpenAI API key']]};
 const providers=()=>Object.entries(labels).map(([id,name])=>({id,name,enabled:true,description:'Fixture provider setup; no live request',configured:['reddit','bluesky','openai'].includes(id)||id==='x'&&!!savedKey,model:id==='openai'?'fixture-model':null,fields:fields[id].map(([name,label])=>({name,label,configured:false,secret:['bearer_token','api_key','app_password','client_secret'].includes(name)}))}));
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
  if(path==='/api/v1/intelligence/scan/status')return route.fulfill({json:{providers:providers(),maximum_assets:5,cache_seconds:300}});
  if(path==='/api/v1/intelligence/scan/latest')return route.fulfill({json:{scan:latest}});
  if(path==='/api/v1/intelligence/scan'){
   scanCalls++;const data=req.postDataJSON();assert.deepEqual(data.assets,[{symbol:'AAPL',asset_class:'stock'},{symbol:'ETH',asset_class:'crypto'}]);assert.equal(data.include_ai,true);latest=report();return route.fulfill({json:latest});
  }
  if(path==='/api/admin/radar/providers')return route.fulfill({json:{providers:providers(),vaultReady}});
  if(path==='/api/admin/radar/vault/initialize'){vaultReady=true;return route.fulfill({json:{vaultReady:true}});}
  if(path==='/api/admin/radar/providers/x'){savedKey=req.postDataJSON().credentials.bearer_token;return route.fulfill({json:{id:'x',configured:true}});}
  return route.fulfill({status:404,json:{detail:'No fixture'}});
 });
 const page=await context.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.clock.install();
 await page.goto(BASE+'/dashboard/opportunities');await page.getByRole('heading',{name:'Opportunity Radar',exact:true}).waitFor();
 assert.equal(scanCalls,0,'Opening Radar must not silently start paid AI calls');
 await page.getByLabel('Watchlist · up to 5 symbols',{exact:true}).fill('AAPL:stock, ETH:crypto');
 await page.getByRole('button',{name:'Scan sources + AI',exact:true}).click();
 await page.getByText('AI research fixture: public evidence requires source verification.',{exact:true}).waitFor();
 assert.ok((await page.getByTestId('radar-source-x').textContent()).includes('Provider rejected API access'));
 assert.ok((await page.getByTestId('radar-source-ethereum').textContent()).includes('native ETH only'));
 assert.ok((await page.getByTestId('radar-source-government').textContent()).includes('Congress'));
 await page.getByRole('navigation',{name:'Radar evidence type'}).getByRole('button',{name:'Social mentions',exact:true}).click();
 await page.getByRole('group',{name:'Social network filter'}).getByRole('button',{name:'Reddit',exact:true}).click();
 await page.getByText('Public Reddit AAPL discussion fixture.',{exact:true}).waitFor();
 assert.equal(await page.getByText('Native ETH large-value transaction fixture; owner and direction unknown.',{exact:true}).count(),0);
 await page.waitForFunction(()=>document.querySelector('[aria-label="Radar evidence type"] button[aria-pressed=true]').textContent==='Social mentions');
 assert.ok(sourceQueries.includes('social'));
 const immediate=page.waitForResponse(response=>response.url().endsWith('/api/v1/intelligence/scan')&&response.request().method()==='POST');
 await page.getByLabel('Auto scan every 5 minutes',{exact:true}).check();await immediate;await page.getByRole('button',{name:'Scan sources + AI',exact:true}).waitFor();assert.equal(scanCalls,2);
 const automatic=page.waitForResponse(response=>response.url().endsWith('/api/v1/intelligence/scan')&&response.request().method()==='POST');
 await page.clock.fastForward(300010);await automatic;await page.getByRole('button',{name:'Scan sources + AI',exact:true}).waitFor();assert.equal(scanCalls,3);
 if(process.env.KAOS_CAPTURE_DIR)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/radar-upgrade.png'});
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.goto(BASE+'/admin/radar');await page.getByTestId('radar-source-settings').waitFor();
 const count=scanCalls;await page.clock.fastForward(300010);assert.equal(scanCalls,count,'Auto-scan interval must stop after leaving Radar');
 await page.getByRole('button',{name:'Initialize private vault',exact:true}).click();await page.getByRole('button',{name:'Verify private vault',exact:true}).waitFor();
 const input=page.getByLabel('X API bearer token',{exact:true});await input.fill('fixture-private-x-token');
 await page.getByRole('button',{name:'Save X',exact:true}).click();await page.getByRole('status').filter({hasText:'X settings saved'}).waitFor();
 assert.equal(savedKey,'fixture-private-x-token');assert.equal(await input.inputValue(),'');assert.ok(!(await page.locator('body').innerText()).includes('fixture-private-x-token'));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('Radar: explicit scan, source failures, whales/government coverage, cited AI, social filter, optional auto-scan cleanup, owner settings, secret clearing and mobile layout passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
