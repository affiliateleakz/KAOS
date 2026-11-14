const BASE=process.env.KAOS_EXTENSION_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN || undefined,headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 await page.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await page.addInitScript(()=>{
  const data={KAOSTargetTabId:42,botRunning:false,kaos_platform:'pocketoption'};
  const state={step:'DASHBOARD',status:'CONNECTED',platform:'pocketoption',license:{authorized:true},entitlements:{chartLimit:1,botAccess:true}};
  window.tabMessages=[];window.testMessages=[]; let signedIn=location.search.includes('restored'), chosen=signedIn;
  const currentState=()=>!signedIn?{step:'LOGIN',status:'LOGGED_OUT'}:chosen?state:{...state,step:'PLATFORM',platform:null};
  const dual=(value,cb)=>{if(cb)queueMicrotask(()=>cb(value));return Promise.resolve(value)};
  window.chrome={runtime:{getURL:p=>location.origin+'/'+p,getManifest:()=>({version:'1.7.16'}),onMessage:{addListener(){}},
   sendMessage:(msg,cb)=>{window.testMessages.push(msg);let reply={ok:true};
    if(msg.type==='KAOS_LOGIN'){signedIn=true;reply={ok:true,state:currentState()};}
    if(msg.type==='KAOS_LOGOUT'){signedIn=false;chosen=false;reply={ok:true};}
    if(msg.type==='KAOS_STARTUP')reply={ok:true,state:currentState()};
    if(msg.type==='KAOS_CONNECT_PLATFORM'){chosen=true;reply={ok:true,state:currentState(),tabId:42};}
    if(msg.type==='KAOS_GET_PLATFORMS')reply={ok:true,platforms:[{id:'pocketoption',name:'Pocket Option',status:'SUPPORTED'}]};
    if(msg.type==='GET_BOT_STATE')reply={running:false};
    return dual(reply,cb);}},
   storage:{onChanged:{addListener(){}},local:{get:(keys,cb)=>dual(data,cb),set:(obj,cb)=>{Object.assign(data,obj);return dual(undefined,cb)},remove:(keys,cb)=>dual(undefined,cb)}},
   tabs:{onUpdated:{addListener(){}},get:(id,cb)=>dual({id,url:'https://pocketoption.com/en/cabinet/demo-quick-high-low/'},cb),query:(opts,cb)=>dual([{id:42,url:'https://pocketoption.com/'}],cb),sendMessage:(id,msg,cb)=>{window.tabMessages.push(msg);if(msg.type==='GET_TERMINAL_SNAPSHOT'){
      const candles=Array.from({length:30},(_,i)=>({ts:1700000000000+i*5000,open:1.1+i*.0001,high:1.101+i*.0001,low:1.099+i*.0001,close:1.1005+i*.0001}));
      return dual({ok:true,readOnly:true,markets:[{asset:'EURUSD',source:'TEST_FIXTURE',candles,ready:false,history:{canonical:30},ai:{},timeframes:{}}],allTrades:[],research:[],aiSummary:{},analytics:{}},cb);
     }return dual({ok:true},cb);} ,create:async()=>({id:42}),update:async()=>({id:42})},
   scripting:{executeScript:async()=>[{result:'12345678'}]},windows:{getCurrent:async()=>({id:1}),update:async()=>({}),onBoundsChanged:{addListener(){}}},downloads:{onChanged:{addListener(){}}}};
 });
 const errors=[];page.on('pageerror',e=>errors.push(e.stack));
 await page.goto(BASE+'/popup.html');
 await page.getByTestId('kaos-login-email').waitFor();
 assert.equal(await page.evaluate(()=>window.testMessages.some(m=>m.type==='KAOS_CONNECT_PLATFORM')),false);
 await page.getByTestId('kaos-login-email').fill('test@example.com');await page.getByTestId('kaos-login-password').fill('test-password');
 await page.getByTestId('kaos-login-submit').click();
 await page.locator('#kaos-broker-overlay.visible').waitFor();
 await page.locator('[data-kaos-broker=pocketoption]').click();
 await page.waitForFunction(()=>document.getElementById('screen-main')?.classList.contains('active'),{timeout:15000});
 const messages=await page.evaluate(()=>window.testMessages);
 assert.ok(messages.some(m=>m.type==='KAOS_CONNECT_PLATFORM'));
 assert.ok(!messages.some(m=>m.type==='START_BOT'));
 await page.waitForFunction(()=>window.tabMessages.filter(m=>m.type==='GET_TERMINAL_SNAPSHOT').length>=2);
 assert.ok(await page.locator('#kaos-dashboard-live canvas').count()>0);
 assert.equal(await page.evaluate(()=>terminalData?.markets?.[0]?.candles?.length),30);
 assert.ok((await page.locator('#terminal-four-grid .mc-name').first().textContent()).includes('EURUSD'));
 console.log('Dashboard received closed-candle fixture data and continued polling without opening Charts.');
 console.log('Actual popup reached charts after fresh sign-in and explicit broker selection, with no START_BOT message.');
 await page.goto(BASE+'/popup.html?restored');
 await page.waitForFunction(()=>document.getElementById('screen-main')?.classList.contains('active'),{timeout:15000});
 assert.ok(!(await page.evaluate(()=>window.testMessages)).some(m=>m.type==='START_BOT'));
 console.log('Restored authorized session also reached charts.');
 await page.locator('[data-testid=kaos-pill-menu]').click();
 await page.locator('[data-testid=kaos-menu-logout]').click();
 await page.getByTestId('kaos-login-email').waitFor();
 await page.waitForTimeout(150);
 const count=await page.evaluate(()=>window.tabMessages.filter(m=>m.type==='GET_TERMINAL_SNAPSHOT').length);
 await page.waitForTimeout(1250);
 assert.equal(await page.evaluate(()=>window.tabMessages.filter(m=>m.type==='GET_TERMINAL_SNAPSHOT').length),count);
 assert.equal(await page.evaluate(()=>terminalData),null);
 assert.deepEqual(errors,[]); console.log('No popup JavaScript errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
