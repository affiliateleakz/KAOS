const BASE=process.env.KAOS_EXTENSION_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN || undefined,headless:true,args:['--no-sandbox']});
 const page=await browser.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.stack));
 await page.route('**/*',route=>{
  if(route.request().url()===BASE+'/__audit_content')return route.fulfill({contentType:'text/html',body:'<body><div data-trader-id="12345678"></div><script src="/candidate7b_strategy.js"></script><script src="/kaos_expiry_collector.js"></script><script src="/content.js"></script></body>'});
  return route.request().url().startsWith(BASE+'/')?route.continue():route.abort();
 });
 await page.addInitScript(()=>{
  const data={};window.fixtureListeners=[];window.fixtureWorkerMessages=[];
  const dual=(value,cb)=>{if(cb)queueMicrotask(()=>cb(value));return Promise.resolve(value)};
  window.chrome={runtime:{getURL:p=>location.origin+'/'+p,getManifest:()=>({version:'1.7.16'}),onMessage:{addListener:cb=>window.fixtureListeners.push(cb)},
   sendMessage:(msg,cb)=>{window.fixtureWorkerMessages.push(msg);return dual((msg.type==='KAOS_STARTUP'||msg.type==='KAOS_SESSION_STATUS')?{ok:true,state:{step:'DASHBOARD',license:{authorized:true},entitlements:{chartLimit:1}}}:{ok:true},cb);}},
   storage:{onChanged:{addListener(){}},local:{get:(keys,cb)=>dual(data,cb),set:(obj,cb)=>{Object.assign(data,obj);return dual(undefined,cb);},remove:(keys,cb)=>dual(undefined,cb)}}};
  window.fixtureRequest=msg=>new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('No core receiver')),3000);let answered=false;
   for(const callback of window.fixtureListeners)callback(msg,{},value=>{if(!answered){answered=true;clearTimeout(timer);resolve(value);}});
  });
 });
 await page.goto(BASE+'/__audit_content');
 await page.waitForTimeout(300);
 const initial=await page.evaluate(()=>fixtureRequest({type:'GET_TERMINAL_SNAPSHOT'}));assert.equal(initial.ok,true);assert.ok(Array.isArray(initial.markets));
 await page.evaluate(()=>{
  const now=Math.floor(Date.now()/5000)*5;
  const records=Array.from({length:25},(_,i)=>({kind:'ohlc',time:now-((25-i)*5)-(i<12?3600:0),open:1.1,high:1.102,low:1.099,close:1.101}));
  window.postMessage({_poat:true,type:'HISTORY_BACKFILL',asset:'EURUSD',records,source:'TEST_FIXTURE'},'*');
 });
 await page.waitForTimeout(300);
 const snapshot=await page.evaluate(()=>fixtureRequest({type:'GET_TERMINAL_SNAPSHOT'}));
 assert.equal(snapshot.ok,true);assert.ok(snapshot.markets[0]?.candles.length>=25,JSON.stringify(snapshot.marketDataDiag));
 assert.ok(snapshot.markets[0].candles.length<=25,'No fabricated gap bars');
 await page.evaluate(()=>window.postMessage({_poat:true,type:'CHART_SLOTS',slots:['EURUSD','GBPUSD','USDJPY','AUDUSD'].map((asset,i)=>({asset,slotId:String(i+1)}))},'*'));
 await page.waitForTimeout(100);
 const status=await page.evaluate(()=>fixtureRequest({type:'GET_COMPANION_STATUS'}));
 assert.equal(status.engineReady,true);assert.equal(status.running,false);
 assert.deepEqual(status.markets.map(row=>row.asset),['EURUSD','GBPUSD','USDJPY','AUDUSD']);
 assert.ok(status.markets.every(row=>Object.keys(row).length===1),'Companion receives labels only, never candle snapshots');
 const after=await page.evaluate(()=>fixtureRequest({type:'GET_TERMINAL_SNAPSHOT'}));assert.equal(after.running,false);
 assert.deepEqual(errors,[]);console.log('Actual content engine returns fixture candles, preserves time gaps and remains stopped without an explicit Start.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
