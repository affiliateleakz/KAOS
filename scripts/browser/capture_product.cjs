// Capture the real KAOS components with labeled sample data. No live API, users or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'apps/web/public/product-previews');
async function serve(folder,spa){const server=http.createServer((req,res)=>{let file=path.resolve(folder,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(folder+path.sep)){res.writeHead(403);return res.end();}if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=spa?path.join(folder,'index.html'):'';if(!file){res.writeHead(404);return res.end();}res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.json':'application/json','.html':'text/html'})[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));return {server,url:'http://127.0.0.1:'+server.address().port};}
(async()=>{
 fs.mkdirSync(out,{recursive:true});const web=await serve(path.join(root,'apps/web/build'),true),extension=await serve(path.join(root,'apps/extension'),false);
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext({viewport:{width:1440,height:960}});const errors=[];
 await context.route('**/*',r=>r.request().url().startsWith(web.url+'/')||r.request().url().startsWith(extension.url+'/')?r.continue():r.abort());
 const rates={free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]};
 const me={id:'demo',username:'kaos_demo',name:'KAOS Demo',role:'user'};
 const ent={tier:'ultimate',community:true,scanners:true,aiInsights:true,botAccess:true,chartLimit:4,deviceLimit:5,modes:['STRATEGY']};
 const coins=['BTC','ETH','SOL','XRP','ADA','DOGE','AVAX','LINK','LTC','DOT','UNI','ATOM','NEAR','BCH','XLM','AAVE','SUI','TON','HBAR','FIL','APT','ARB','OP','INJ'].map((symbol,i)=>({symbol,name:({BTC:'Bitcoin',ETH:'Ethereum',SOL:'Solana'})[symbol]||symbol,price_usd:100+i,market_cap:(26-i)**3*1e6,volume_24h:(25-i)*1e6,change_1h:(i%2?1:-1)*i/20,change_24h:(i%2?1:-1)*(.4+i/4),change_7d:i-10,change_30d:i-12,change_1y:i-15,source:'Example data'}));
 await context.route('**/api/**',route=>{
  const request=route.request(),uri=new URL(request.url()),p=uri.pathname;
  const json=value=>route.fulfill({json:value});
  if(p==='/api/auth/me')return json(me);
  if(p==='/api/notifications'||p==='/api/affiliate/marketing')return json([]);
  if(p==='/api/v1/trading/config')return json({entitlements:ent});
  if(p==='/api/v1/intelligence/news/feed')return json({state:'complete',articles:[{title:'Example research briefing',summary:'Use news, price structure and disclosures together before reviewing a setup.',source:'Example data',source_url:'https://example.com',published_at:new Date().toISOString(),tickers:['MSFT']}]});
  if(p==='/api/v1/intelligence/signals/opportunities')return json({state:'complete',market:'stocks',timeframe:'any',scanned:16,universe_size:16,coverage:[],execution_enabled:false,plays:[{symbol:'MSFT',asset_class:'stock',direction:'BUY',score:78,timeframe:'daily',planning:true,basis:'Evidence-scored example · AI has not confirmed this setup',model_state:'collecting',reason:'Example research setup. Review fresh prices and available evidence before making a decision.',reference_entry:100,reference_stop:97,reference_target:106,reward_risk:2,horizon:'1 trading session',source:'Example data',source_time:new Date().toISOString(),expires_at:new Date(Date.now()+900000).toISOString(),coverage_percent:35,context_level:'Limited evidence',score_components:{trend:25,momentum:20}}]});
  if(p==='/api/v1/crypto/market')return json({coins,count:coins.length,provider:'Example data',weighting:'market_cap',failures:[],as_of:new Date().toISOString(),cached:true});
  if(p==='/api/v1/crypto/pairs')return json({pairs:[]});
  if(p==='/api/community/posts')return json({items:[{id:'example_post',authorId:'example_creator',kind:'discussion',title:'What do you look for before an entry?',body:'Example discussion: share the price structure, timeframe and risk checks behind your setup. Follow other members and compare your ideas.',author:{id:'example_creator',username:'demo_trader',displayName:'Demo Trader'},likesCount:0,commentsCount:0,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),isFollowing:false,canDelete:false}],nextCursor:null});
  if(p==='/api/affiliate/program')return json({enrollmentEnabled:true,payoutsEnabled:false,holdDays:30,tier:'free',rates});
  if(p==='/api/affiliate/overview')return json({active:true,referralLink:'https://tradingwithkaos.com/register?ref=KAOS-DEMO',clicks:0,signups:0,payingReferrals:0,pending:0});
  if(p==='/api/affiliate/ledger')return json({tier:'free',balance:{pending:'0',available:'0',reversed:'0',paid:'0'},entries:[]});
  if(p==='/api/affiliate/connect/status')return json({configured:false,transfersEnabled:false});
  return route.fulfill({status:404,json:{detail:'Example preview: endpoint not used'}});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 async function capture(file){await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(img=>img.decode().catch(()=>{})));const badge=document.createElement('div');badge.id='capture-label';badge.textContent='CURRENT KAOS UI · EXAMPLE DATA';badge.style.cssText='position:fixed;right:12px;top:12px;z-index:2147483647;background:#17180e;color:#e8c46f;border:1px solid #9e7b35;border-radius:5px;padding:8px 12px;font:10px system-ui;letter-spacing:.06em';document.body.appendChild(badge);});await page.screenshot({path:path.join(out,file),fullPage:false});await page.locator('#capture-label').evaluate(el=>el.remove());}
 await page.goto(web.url+'/dashboard/opportunities');await page.getByRole('heading',{name:'KAOS Radar',exact:true}).waitFor();
 await page.getByRole('navigation',{name:'Radar sections'}).getByRole('button',{name:'AI Signal',exact:true}).click();await page.getByRole('heading',{name:'1. MSFT · BUY',exact:true}).waitFor();
 await page.getByLabel('Opportunity timeframe',{exact:true}).selectOption('any');await page.getByRole('heading',{name:'1. MSFT · BUY',exact:true}).waitFor();await capture('radar.png');
 await page.goto(web.url+'/dashboard/crypto-scanner');await page.waitForFunction(()=>document.querySelectorAll('[data-bubble-id]').length===24);await capture('heatmap.png');
 await page.goto(web.url+'/dashboard/community');await page.getByRole('heading',{name:'What do you look for before an entry?',exact:true}).waitFor();await capture('community.png');
 await page.goto(web.url+'/dashboard/affiliate');await page.getByTestId('affiliate-link').waitFor();await capture('affiliate.png');
 await page.addInitScript(()=>{
  const ent={chartLimit:4,botAccess:true},saved={KAOSTargetTabId:42,botRunning:false,kaos_platform:'pocketoption',kaosEntitlements:ent,kaosChartCount:4};
  const state={step:'DASHBOARD',status:'CONNECTED',platform:'pocketoption',license:{authorized:true},entitlements:ent};const dual=(value,cb)=>{if(cb)queueMicrotask(()=>cb(value));return Promise.resolve(value);};
  window.captureStarts=0;
  window.chrome={runtime:{getURL:p=>location.origin+'/'+p,getManifest:()=>({version:'1.7.30'}),onMessage:{addListener(){}},sendMessage:(msg,cb)=>{if(msg.type==='START_BOT')window.captureStarts++;return dual(msg.type==='KAOS_GET_PLATFORMS'?{ok:true,platforms:[{id:'pocketoption',name:'Pocket Option',status:'SUPPORTED'}]}:msg.type==='GET_BOT_STATE'?{running:false}:{ok:true,state,tabId:42},cb);}},storage:{onChanged:{addListener(){}},local:{get:(keys,cb)=>dual(saved,cb),set:(obj,cb)=>{Object.assign(saved,obj);return dual(undefined,cb)},remove:(keys,cb)=>dual(undefined,cb)}},tabs:{onUpdated:{addListener(){}},get:(id,cb)=>dual({id,url:'https://pocketoption.com/en/cabinet/demo-quick-high-low/'},cb),query:(opts,cb)=>dual([{id:42,url:'https://pocketoption.com/'}],cb),sendMessage:(id,msg,cb)=>dual({ok:true,engineReady:true,asset:'EURUSD',accountIsDemo:true,accountBalance:1000,running:false,markets:['EURUSD','GBPUSD','USDJPY','AUDUSD'].map(asset=>({asset}))},cb),create:async()=>({id:42}),update:async()=>({id:42})},scripting:{executeScript:async()=>[{result:'demo'}]},windows:{getCurrent:async()=>({id:1}),update:async()=>({}),onBoundsChanged:{addListener(){}}},downloads:{onChanged:{addListener(){}}}};
 });
 await page.setViewportSize({width:1280,height:900});await page.goto(extension.url+'/popup.html');await page.waitForFunction(()=>document.getElementById('screen-main')?.classList.contains('active'));
 await page.locator('#screen-main [data-session-status=account]').filter({hasText:'DEMO ACCOUNT'}).waitFor();await page.getByLabel('How many charts do you want to trade',{exact:true}).selectOption('4');await page.waitForTimeout(1500);await capture('bot.png');assert.equal(await page.evaluate(()=>window.captureStarts),0);
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'provenance.json'),JSON.stringify({kind:'Actual KAOS interface captures',data:'Labeled local fixtures; no real accounts, trades or performance claims',botVersion:'1.7.30',views:['bot','radar','heatmap','community','affiliate'],generator:'scripts/browser/capture_product.cjs'},null,2)+'\n');
 console.log('Captured five actual product views with example data and no Start/order messages.');
 }finally{await browser.close();web.server.close();extension.server.close();}
})().catch(e=>{console.error(e);process.exit(1)});
