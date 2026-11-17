// Authenticated owner model loading and paper controls; all providers use local fixtures.
const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL,root=path.resolve(__dirname,'../..');
 const model=JSON.parse(fs.readFileSync(root+'/downloads/KAOS-Micro-Reversion-Paper-Model.json'));
 const fixture=JSON.parse(fs.readFileSync(root+'/apps/extension/fixtures/micro-paper-parity.json'));
 const seconds=fixture.rows.flatMap(b=>Array.from({length:5},(_,i)=>[b.ts+i*1000,String(b.open),String(b.high),String(b.low),String(b.close),'1',b.ts+i*1000+999,'1',1]));
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900},acceptDownloads:true});const errors=[],providerCalls=[];let role='super_admin',modelRequests=0;page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{
  const request=route.request(),url=new URL(request.url()),p=url.pathname;
  if(url.origin==='https://data-api.binance.vision'){
   assert.equal(request.method(),'GET');assert.equal(request.headers().authorization,undefined);providerCalls.push(p);
   if(p==='/api/v3/time')return route.fulfill({json:{serverTime:fixture.rows.at(-1).closeTs}});
   const limit=Number(url.searchParams.get('limit')),end=url.searchParams.get('endTime');return route.fulfill({json:seconds.filter(r=>!end||r[0]<=Number(end)).slice(-limit)});
  }
  if(url.origin!==new URL(BASE).origin)return route.abort();
  if(!p.startsWith('/api/'))return route.continue();
  if(p==='/api/auth/me')return route.fulfill({json:{id:'fixture',role,name:'Owner',membership_status:'ACTIVE',membership_plan:role==='super_admin'?'ultimate':'pro'}});
  if(p==='/api/notifications')return route.fulfill({json:[]});
  if(p==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{tier:role==='super_admin'?'ultimate':'pro',aiInsights:true,aiTraining:true,pretrainedModels:role==='super_admin'}}});
  if(p==='/api/v1/ai/training/status')return route.fulfill({json:{personalModels:[],sharedModels:[],jobs:[],personalSamples:0,minimumSamples:500,worker:{running:false},personalTraining:true,pretrainedAccess:role==='super_admin',notice:'Required service learning'}});
  if(p==='/api/v1/ai/research/micro-reversion'){modelRequests++;assert.equal(role,'super_admin');return route.fulfill({json:{model,researchOnly:true,executionEnabled:false,state:'failed_adverse_fill_gate'}});}
  return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
 });
 await page.goto(BASE+'/dashboard/kaos-ai');await page.getByRole('button',{name:'Open experimental paper test',exact:true}).click();
 await page.getByText('Model loaded from KAOS.',{exact:false}).waitFor();assert.equal(modelRequests,1);assert.equal(providerCalls.length,0);
 assert.equal(await page.getByRole('button',{name:'Start live paper feed',exact:true}).isEnabled(),true);
 await page.getByRole('button',{name:'Start live paper feed',exact:true}).click();await page.getByText('Live crypto paper observation started.',{exact:false}).waitFor();assert.deepEqual(providerCalls,['/api/v3/time','/api/v3/klines','/api/v3/klines']);
 await page.getByRole('button',{name:'Stop paper feed',exact:true}).click();
 await page.getByText('Replay a candle file instead',{exact:true}).click();
 await page.getByLabel('Paper candle JSON',{exact:true}).setInputFiles({name:'BTCUSDT_5s.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({markets:{BTCUSDT:fixture.rows}}))});
 await page.getByText('Historical paper replay complete.',{exact:false}).waitFor();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export paper results',exact:true}).click();const exported=JSON.parse(fs.readFileSync(await (await download).path()));assert.equal(exported.executionEnabled,false);assert.equal(exported.mode,'historical-replay');assert.equal(exported.adverseEntryBps,1);assert.ok(exported.results.length>0);
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 role='user';await page.reload();await page.getByTestId('personal-ai-workspace').waitFor();assert.equal(await page.getByRole('button',{name:'Open experimental paper test',exact:true}).count(),0);assert.equal(modelRequests,1);assert.deepEqual(errors,[]);
 console.log('Website paper lab: owner-only automatic model, no initial feed calls, explicit live paper Start/Stop, local replay/export, unchanged Pro access and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
