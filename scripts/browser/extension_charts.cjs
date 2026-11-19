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
    if((msg.type==='KAOS_STARTUP'||msg.type==='KAOS_SESSION_STATUS'))reply={ok:true,state:currentState()};
    if(msg.type==='KAOS_CONNECT_PLATFORM'){chosen=true;reply={ok:true,state:currentState(),tabId:42};}
    if(msg.type==='KAOS_GET_PLATFORMS')reply={ok:true,platforms:[{id:'pocketoption',name:'Pocket Option',status:'SUPPORTED'}]};
    if(msg.type==='GET_BOT_STATE')reply={running:false};
    return dual(reply,cb);}},
   storage:{onChanged:{addListener(){}},local:{get:(keys,cb)=>dual(data,cb),set:(obj,cb)=>{Object.assign(data,obj);return dual(undefined,cb)},remove:(keys,cb)=>dual(undefined,cb)}},
   tabs:{onUpdated:{addListener(){}},get:(id,cb)=>dual({id,url:'https://pocketoption.com/en/cabinet/demo-quick-high-low/'},cb),query:(opts,cb)=>dual([{id:42,url:'https://pocketoption.com/'}],cb),sendMessage:(id,msg,cb)=>{window.tabMessages.push(msg);if(msg.type==='GET_COMPANION_STATUS'&&window.fixtureDisconnected)return Promise.reject(Error('Broker unavailable'));if(msg.type==='GET_COMPANION_STATUS')return dual({ok:true,engineReady:true,asset:'EURUSD',markets:[{asset:'EURUSD'},{asset:'GBPUSD'},{asset:'USDJPY'},{asset:'AUDUSD'}],accountIsDemo:window.fixtureDemo??null,accountBalance:1000,running:false},cb);if(msg.type==='GET_TERMINAL_SNAPSHOT'){
      const candles=Array.from({length:30},(_,i)=>({ts:1700000000000+i*5000,open:1.1+i*.0001,high:1.101+i*.0001,low:1.099+i*.0001,close:1.1005+i*.0001}));
      return dual({ok:true,readOnly:true,accountIsDemo:window.fixtureDemo??null,markets:[{asset:'EURUSD',source:'TEST_FIXTURE',candles,ready:false,history:{canonical:30},ai:{},timeframes:{}}],allTrades:[],research:[],aiSummary:{},analytics:{}},cb);
     }return dual({ok:true},cb);} ,create:async()=>({id:42}),update:async()=>({id:42})},
   scripting:{executeScript:async()=>[{result:'12345678'}]},windows:{getCurrent:async()=>({id:1}),update:async()=>({}),onBoundsChanged:{addListener(){}}},downloads:{onChanged:{addListener(){}}}};
 });
 const errors=[];page.on('pageerror',e=>errors.push(e.stack));
 await page.goto(BASE+'/popup.html');
 await page.getByTestId('kaos-login-email').waitFor();
 assert.equal(await page.getByLabel('Email address',{exact:true}).count(),1);
 assert.equal(await page.getByLabel('Password',{exact:true}).count(),1);
 await page.getByTestId('kaos-login-submit').click();
 await page.getByRole('alert').filter({hasText:'Enter your email address and password.'}).waitFor();
 assert.ok(!(await page.evaluate(()=>window.testMessages)).some(m=>m.type==='KAOS_LOGIN'));
 await page.setViewportSize({width:390,height:844});
 assert.ok((await page.getByTestId('kaos-login-panel').boundingBox()).width<=390);
 await page.setViewportSize({width:1280,height:900});
 assert.equal(await page.locator('.kaos-brand-title').evaluate(el=>getComputedStyle(el).color),'rgb(232, 196, 111)');
 assert.ok((await page.getByTestId('kaos-login-submit').evaluate(el=>getComputedStyle(el).backgroundImage)).includes('232, 196, 111'));
 if(process.env.KAOS_CAPTURE_DIR)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/extension-login.png'});
 assert.equal(await page.evaluate(()=>window.testMessages.some(m=>m.type==='KAOS_CONNECT_PLATFORM')),false);
 await page.getByTestId('kaos-login-email').fill('test@example.com');await page.getByTestId('kaos-login-password').fill('test-password');
 await page.getByTestId('kaos-login-submit').click();
 await page.locator('#kaos-broker-overlay.visible').waitFor();
 await page.locator('[data-kaos-broker=pocketoption]').click();
 await page.waitForFunction(()=>document.getElementById('screen-main')?.classList.contains('active'),{timeout:15000});
 const messages=await page.evaluate(()=>window.testMessages);
 assert.ok(messages.some(m=>m.type==='KAOS_CONNECT_PLATFORM'));
 assert.ok(!messages.some(m=>m.type==='START_BOT'));
 await page.waitForFunction(()=>window.tabMessages.some(m=>m.type==='GET_COMPANION_STATUS'));
 assert.equal(await page.locator('#kaos-dashboard-live').isVisible(),false);
 assert.equal(await page.locator('#screen-chart').isVisible(),false);
 assert.equal(await page.evaluate(()=>window.tabMessages.filter(m=>m.type==='GET_TERMINAL_SNAPSHOT').length),0);
 assert.ok((await page.locator('[data-companion-asset]').textContent()).includes('EURUSD'));
 assert.ok(await page.getByRole('heading',{name:'Trading dashboard',exact:true}).isVisible());
 const chartCount=page.getByRole('combobox',{name:'How many charts do you want to trade',exact:true});
 assert.ok(await chartCount.isVisible(),'Broker chart count belongs on the main Bot tab');
 assert.equal(await chartCount.locator('option[value="4"]').isDisabled(),true,'One-chart plan must not unlock four');
 await page.evaluate(()=>kaosApplyChartLimit({chartLimit:4}));
 await chartCount.selectOption('4');
 const selectedConfig=await page.evaluate(()=>getStrategyBuilderStartConfig());
 assert.equal(selectedConfig.chartCount,4);assert.equal(selectedConfig.strategySlots.length,4);
 assert.deepEqual(selectedConfig.strategySlots.map(row=>row.asset),['EURUSD','GBPUSD','USDJPY','AUDUSD']);
 await page.getByRole('button',{name:'SHOW POCKET OPTION',exact:true}).click();
 assert.equal(await page.locator('#screen-chart').isVisible(),false,'Broker focus must not reopen internal charts');
 assert.equal(await page.evaluate(()=>chrome.storage.local.get(['kaosChartCount']).then(r=>r.kaosChartCount)),4);
 await page.evaluate(()=>kaosApplyChartLimit({chartLimit:1}));
 assert.equal(await chartCount.inputValue(),'1','Plan downgrade clamps the selection');
 assert.equal(await page.locator('.kaos-companion-brand').getAttribute('src'),'assets/kaos-logo-horizontal.png');

 assert.equal(await page.locator('#debug-fold').count(),1);
 assert.equal(await page.locator('#screen-main .dashboard-top #debug-fold').count(),1);
 await page.locator('#debug-fold > summary').click();
 assert.equal(await page.locator('#debug-fold').evaluate(el=>el.open),true);
 assert.ok(await page.locator('#dbg-asset').isVisible());
 await page.evaluate(()=>window.kaosRoute('settings'));
 assert.equal(await page.locator('#debug-fold').isVisible(),false);
 await page.locator('#k14-head-diag').evaluate(button=>button.click());
 await page.waitForFunction(()=>document.getElementById('screen-main').classList.contains('view-dashboard'));
 assert.ok(await page.locator('#dbg-asset').isVisible());
 await page.locator('#debug-fold > summary').click();
 console.log('Companion receives minimal broker status without chart snapshots or automatic Start.');
 await page.goto(BASE+'/popup.html?restored');
 await page.waitForFunction(()=>document.getElementById('screen-main')?.classList.contains('active'),{timeout:15000});
 assert.ok(!(await page.evaluate(()=>window.testMessages)).some(m=>m.type==='START_BOT'));
 assert.equal(await page.getByRole('button',{name:'Open paper test',exact:true}).isVisible(),true);
 console.log('Restored authorized session reached the companion.');
 await page.waitForFunction(()=>window.__kaosChartSessionInitialized===true);
 const checksBefore=await page.evaluate(()=>window.testMessages.filter(m=>m.type==='KAOS_STARTUP').length);
 await page.evaluate(async()=>{await startFlow();await startFlow();});
 assert.equal(await page.evaluate(()=>window.testMessages.filter(m=>m.type==='KAOS_STARTUP').length),checksBefore);
 assert.equal(await page.locator('#screen-checking').isVisible(),false);
 await page.waitForFunction(()=>document.body.classList.contains('kaos-mini'));
 await page.setViewportSize({width:430,height:800});
 assert.ok((await page.locator('#screen-main .kaos-app-workspace').boundingBox()).width<=430);
 await page.locator('#screen-main [data-session-size]').filter({hasText:'Expand'}).waitFor();
 await page.locator('#screen-main [data-session-size]').click();
 await page.setViewportSize({width:1280,height:900});
 await page.waitForFunction(()=>document.body.classList.contains('kaos-max'));
 await page.evaluate(()=>window.kaosRoute('dashboard'));
 await page.setViewportSize({width:430,height:800});
 const mainNav=page.locator('#screen-main .kaos-companion-nav');
 assert.equal(await mainNav.getByRole('link').getAttribute('href'),'https://tradingwithkaos.com/dashboard');
 for(const [view,label] of [['history','Trades'],['risk','Risk'],['settings','Settings'],['strategy','Strategy'],['dashboard','Bot']]){
  await mainNav.getByRole('button',{name:label,exact:true}).click();
  await page.waitForFunction(view=>document.getElementById('screen-main').classList.contains('view-'+view),view);
 }
 await page.waitForFunction(()=>terminalData?.engineReady===true);
 assert.equal(await page.locator('#screen-main .kaos-session-strip').count(),1);
 assert.equal(await page.locator('#screen-main .kaos-session-strip').isVisible(),true);
 assert.ok((await page.locator('#screen-main .kaos-session-strip').boundingBox()).y<120);
 assert.ok((await page.locator('#screen-main .kaos-session-strip').textContent()).includes('BOT STOPPED'));
 const accountBox=await page.locator('#screen-main .k14-acct').boundingBox();
 const tradesBox=await page.locator('#screen-main .k14-trades').boundingBox();
 assert.ok(tradesBox.y>=accountBox.y+accountBox.height,'Account and trades cards must not overlap');
 assert.ok(accountBox.height>200,'Account card must retain room for status and statistics');
 const toolbarBox=await page.locator('#screen-main .kaos-banner-toolbar').boundingBox();
 const startBox=await page.locator('#start-btn').boundingBox();
 assert.ok(startBox.y>=toolbarBox.y+toolbarBox.height,'Start must not overlap the settings');
 assert.ok(await page.locator('#kaos-strategy-box').isVisible());


 if(process.env.KAOS_CAPTURE_DIR){await page.setViewportSize({width:430,height:800});await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/extension-dashboard.png'});await page.setViewportSize({width:1280,height:900});}
 assert.ok(!(await page.evaluate(()=>window.testMessages)).some(m=>m.type==='START_BOT'));
 await page.evaluate(()=>{window.fixtureDemo=true;terminalData.accountIsDemo=true;});
 await page.locator('#screen-main [data-session-status=account]').filter({hasText:'DEMO ACCOUNT'}).waitFor();
 await page.evaluate(()=>{window.fixtureDemo=false;terminalData.accountIsDemo=false;state.running=true;});
 await page.locator('#screen-main [data-session-status=account]').filter({hasText:'REAL ACCOUNT'}).waitFor();
 await page.locator('#screen-main [data-session-status=bot]').filter({hasText:'BOT RUNNING'}).waitFor();
 await page.locator('#screen-main [data-session-stop]').click();
 assert.equal(await page.evaluate(()=>state.running),false);
 assert.ok((await page.evaluate(()=>window.testMessages)).some(m=>m.type==='STOP_BOT'));
 await page.evaluate(async()=>{window.fixtureDisconnected=true;await kaosRefreshCompanionStatus();});
 await page.locator('#screen-main [data-session-status=connection]').filter({hasText:'Broker connection unconfirmed'}).waitFor();
 await page.locator('#screen-main [data-session-status=account]').filter({hasText:'Account type unconfirmed'}).waitFor();
 assert.equal(await page.locator('[data-companion-asset]').textContent(),'No current market confirmed');
 assert.ok((await page.locator('[data-companion-guidance]').textContent()).includes('bot may still be running'));
 await page.evaluate(async()=>{window.fixtureDisconnected=false;await kaosRefreshCompanionStatus();});
 await page.locator('#screen-main [data-session-status=connection]').filter({hasText:'Broker responding'}).waitFor();
 assert.equal(await mainNav.locator('[aria-current=page]').textContent(),'Bot');
 await page.evaluate(()=>{kaosStopChartFeed();terminalData={engineReady:true,asset:'EURUSD',accountIsDemo:false};kaosCompanionStatusAt=Date.now()-16000;});
 await page.locator('#screen-main [data-session-status=connection]').filter({hasText:'Broker connection unconfirmed'}).waitFor();
 await page.locator('#screen-main [data-session-status=account]').filter({hasText:'Account type unconfirmed'}).waitFor();
 await page.evaluate(()=>{kaosApplyChartLimit({chartLimit:4});kaosApplyChartCount(4);});
 const startedBefore=await page.evaluate(()=>window.testMessages.filter(m=>m.type==='START_BOT').length);
 await page.locator('#start-btn').click();
 await page.waitForFunction(n=>window.testMessages.filter(m=>m.type==='START_BOT').length>n,startedBefore);
 const start=await page.evaluate(()=>window.testMessages.filter(m=>m.type==='START_BOT').at(-1));
 assert.equal(start.chartCount,4);assert.equal(start.multiAsset,true);assert.equal(start.strategySlots.length,4);
 await page.evaluate(()=>stopBot());
 console.log('Gold login, four-chart Bot selection, plan limits, explicit Start payload, broker focus, account status and Stop passed.');
 await page.locator('[data-testid=kaos-pill-menu]').click();
 await page.locator('[data-testid=kaos-menu-logout]').click();
 await page.getByTestId('kaos-login-email').waitFor();
 await page.waitForTimeout(150);
 const count=await page.evaluate(()=>window.tabMessages.filter(m=>m.type==='GET_COMPANION_STATUS').length);
 await page.waitForTimeout(1250);
 assert.equal(await page.evaluate(()=>window.tabMessages.filter(m=>m.type==='GET_COMPANION_STATUS').length),count);
 assert.equal(await page.evaluate(()=>terminalData),null);
 assert.deepEqual(errors,[]); console.log('No popup JavaScript errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
