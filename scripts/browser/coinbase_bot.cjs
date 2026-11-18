const {chromium}=require('../../apps/web/node_modules/playwright');const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_EXTENSION_PREVIEW_URL,browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>r.request().url().startsWith(BASE+'/')?r.continue():r.abort());
 await page.addInitScript(()=>{
  const data={kaosSelectedBroker:'coinbase',botRunning:false,KAOSTargetTabId:42,settings:{amount:17.25,martingale:false,compound:false,autoCooldownOn:true,profitTarget:80,dailyLossLimit:35,maxLossStreak:3,cooldownAfterLoss:45}};
  const cloud={step:'DASHBOARD',status:'CONNECTED',platform:'pocketoption',license:{authorized:true},entitlements:{chartLimit:4,botAccess:true}};
  let run='STOPPED';window.messages=[];const dual=(v,cb)=>{if(cb)queueMicrotask(()=>cb(v));return Promise.resolve(v);};
  window.chrome={runtime:{getURL:p=>location.origin+'/'+p,getManifest:()=>({version:'1.7.34'}),onMessage:{addListener(){}},sendMessage:(msg,cb)=>{
   window.messages.push(msg);let reply={ok:true};
   if(['KAOS_STARTUP','KAOS_SESSION_STATUS'].includes(msg.type))reply={ok:true,state:cloud};
   if(msg.type==='GET_BOT_STATE')reply={running:false};
   if(msg.type==='KAOS_GET_PLATFORMS')reply={ok:true,platforms:[]};
   if(msg.type==='KAOS_BROKER_VAULT')reply={ok:true,data:msg.path.endsWith('/products')?{products:[{product_id:'BTC-USD'},{product_id:'ETH-USD'}]}:{saved:true}};
   if(msg.type==='KAOS_COINBASE_BOT'){
    if(msg.action==='start')run='RUNNING';if(msg.action==='stop')run='STOPPING';
    reply={ok:true,data:{state:run,workerReady:true,detail:'Fixture Coinbase session'}};
   }
   return dual(reply,cb);
  }},storage:{onChanged:{addListener(){}},local:{get:(keys,cb)=>dual(data,cb),set:(obj,cb)=>{Object.assign(data,obj);return dual(undefined,cb)},remove:(_,cb)=>dual(undefined,cb)}},
  tabs:{onUpdated:{addListener(){}},query:(_,cb)=>dual([],cb),get:(id,cb)=>dual({id,url:'https://pocketoption.com/'},cb),sendMessage:(_,msg,cb)=>dual({ok:true,markets:[]},cb),create:async()=>({id:42}),update:async()=>({})},
  scripting:{executeScript:async()=>[]},windows:{getCurrent:async()=>({id:1}),update:async()=>({}),onBoundsChanged:{addListener(){}}},downloads:{onChanged:{addListener(){}}}};
 });
 await page.goto(BASE+'/popup.html?restored');
 await page.locator('#kaos-coinbase-bot-panel').waitFor({state:'visible'});
 assert.equal((await page.evaluate(()=>window.messages)).filter(m=>m.type==='KAOS_COINBASE_BOT'&&m.action==='start').length,0);
 await page.locator('#kaos-coinbase-markets').click();await page.locator('#kaos-coinbase-products').selectOption(['BTC-USD','ETH-USD']);
 await page.evaluate(async()=>{await window.KAOSCoinbaseBot.ready();kaosApplyChartLimit({chartLimit:4});kaosApplyChartCount(2);});
 assert.equal(await page.locator('#amount-input').inputValue(),'17.25');
 assert.equal(await page.locator('#kaos-amount-input').inputValue(),'17.25');
 page.once('dialog',d=>d.dismiss());await page.locator('#start-btn').click();
 assert.equal((await page.evaluate(()=>window.messages)).filter(m=>m.type==='KAOS_COINBASE_BOT'&&m.action==='start').length,0);
 page.once('dialog',d=>d.accept());await page.locator('#start-btn').click();
 await page.waitForFunction(()=>window.messages.some(m=>m.type==='KAOS_COINBASE_BOT'&&m.action==='start'));
 const start=(await page.evaluate(()=>window.messages)).find(m=>m.type==='KAOS_COINBASE_BOT'&&m.action==='start');
 assert.equal(start.payload.settings.amount,17.25);assert.equal(start.payload.settings.chartCount,2);
 assert.equal(start.payload.settings.dailyLossLimit,35);assert.equal(start.payload.settings.profitTarget,80);
 assert.equal(start.payload.settings.maxLossStreak,3);assert.equal(start.payload.settings.cooldownAfterLoss,45);
 assert.equal(start.payload.settings.martingale,false);assert.deepEqual(start.payload.products,['BTC-USD','ETH-USD']);
 assert.equal((await page.evaluate(()=>window.messages)).filter(m=>m.type==='START_BOT').length,0,'Coinbase must never dispatch Pocket Option Start');
 await page.locator('#start-btn').click();await page.waitForFunction(()=>window.messages.some(m=>m.type==='KAOS_COINBASE_BOT'&&m.action==='stop'));
 assert.equal(await page.locator('#kaos-expiry-select').isDisabled(),true);
 assert.deepEqual(errors,[]);
 console.log('Coinbase main bot: existing amount and risk controls, chart count, explicit real-money Start/cancel, broker separation and Stop passed. No real orders.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
