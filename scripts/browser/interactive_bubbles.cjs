// Local fixture feeds only: exercises the real crypto page, no broker or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext();let marketCalls=0,pairCalls=0,fallback=false;
 const coins=Array.from({length:36},(_,i)=>({symbol:i===0?'BTC':i===1?'SOL':'COIN'+i,name:i===0?'Bitcoin':i===1?'Solana':'Coin '+i,price_usd:100+i,market_cap:(36-i)**3*1e6,volume_24h:(i+1)*1e6,change_1h:i===0?0:.1*i,change_24h:i%2?i/2:-i/3,change_7d:i-12,change_30d:i-18,change_1y:i-20,source:'Fixture',url:'https://www.coingecko.com/en/coins/fixture-'+i}));
 await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await context.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/auth/me')return route.fulfill({json:{id:'fixture',name:'Owner',role:'super_admin'}});
  if(path==='/api/notifications')return route.fulfill({json:[]});
  if(path==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{tier:'ultimate',scanners:true,chartLimit:4}}});
  if(path==='/api/v1/crypto/market'){marketCalls++;return route.fulfill({json:{coins:coins.map(c=>fallback?{...c,market_cap:null,change_1h:null,change_7d:null,change_30d:null,change_1y:null}:c),count:36,provider:'Fixture',weighting:fallback?'24h_volume':'market_cap',failures:[],as_of:'2026-11-15T12:00:00Z',cached:true}});}
  if(path==='/api/v1/crypto/pairs'){pairCalls++;return route.fulfill({json:{pairs:[]}});}
  return route.fulfill({status:404,json:{detail:'No fixture'}});
 });
 const page=await context.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(BASE+'/dashboard/crypto-scanner');
 const map=page.getByTestId('bubble-map'),nodes=map.locator('[data-bubble-id]');
 await page.waitForFunction(()=>document.querySelectorAll('[data-bubble-id]').length===36);
 await map.scrollIntoViewIfNeeded();
 const bitcoin=map.getByRole('button',{name:/^BTC Bitcoin,/});
 const first=await bitcoin.getAttribute('transform');await page.waitForTimeout(350);
 assert.notEqual(await bitcoin.getAttribute('transform'),first,'Bubbles should drift');
 await map.getByRole('button',{name:'Animate bubbles',exact:true}).click();
 await page.waitForTimeout(80);const paused=await bitcoin.getAttribute('transform');await page.waitForTimeout(120);
 assert.equal(await bitcoin.getAttribute('transform'),paused,'Paused bubbles must stop');
 const box=await bitcoin.boundingBox();const beforeDrag=await bitcoin.getAttribute('transform');
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+35,box.y+box.height/2+25,{steps:8});await page.mouse.up();
 assert.notEqual(await bitcoin.getAttribute('transform'),beforeDrag,'Dragging should move a bubble');
 assert.equal(await page.getByTestId('bubble-detail').count(),0,'A drag must not open details');
 await bitcoin.focus();await page.keyboard.press('Enter');
 await page.getByRole('region',{name:'Asset details'}).waitFor();
 assert.ok((await page.getByTestId('bubble-detail').textContent()).includes('Bitcoin'));
 assert.equal(context.pages().length,1,'Coin selection must not open an external tab');
 await page.keyboard.press('Escape');assert.equal(await page.getByTestId('bubble-detail').count(),0);
 const period=page.getByRole('group',{name:'Bubble timeframe'});
 await period.getByRole('button',{name:'30d',exact:true}).click();assert.equal(await bitcoin.getAttribute('data-change'),'-18');
 await page.getByLabel('Bubble size',{exact:true}).selectOption('market_cap');
 assert.ok((await map.textContent()).includes('Size: market cap'));
 await page.getByLabel('Search coins',{exact:true}).fill('Solana');assert.equal(await nodes.count(),1);
 await nodes.first().focus();await page.keyboard.press('Enter');
 await page.getByRole('button',{name:'Add to watchlist',exact:true}).click();
 await page.getByRole('button',{name:'Close asset details'}).click();
 await page.getByLabel('Search coins',{exact:true}).fill('');
 await page.getByRole('button',{name:/Watchlist only/}).click();assert.equal(await nodes.count(),1);
 assert.ok((await nodes.first().getAttribute('aria-label')).startsWith('SOL'));
 assert.equal(marketCalls,1);assert.equal(pairCalls,1,'UI controls must not refetch provider data');
 await page.reload();await page.waitForFunction(()=>document.querySelectorAll('[data-bubble-id]').length===36);
 await page.getByRole('button',{name:/Watchlist only/}).click();assert.equal(await nodes.count(),1,'Watchlist should survive reload');
 await page.getByRole('button',{name:/Show all coins/}).click();
 await page.getByLabel('Coin range').selectOption('20');assert.equal(await nodes.count(),20);
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('[aria-label="Animate bubbles"]').getAttribute('aria-pressed')==='false');assert.equal(await map.getByRole('button',{name:'Animate bubbles'}).getAttribute('aria-pressed'),'false');
 if(process.env.KAOS_CAPTURE_DIR){await map.scrollIntoViewIfNeeded();await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/interactive-crypto-bubbles.png'});}
 fallback=true;await period.getByRole('button',{name:'Refresh',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('[aria-label="Bubble timeframe"] button').disabled);
 assert.equal(await period.getByRole('button',{name:'30d',exact:true}).isDisabled(),true);
 await period.getByRole('button',{name:'24h',exact:true}).click();
 assert.equal(await bitcoin.getAttribute('data-change'),'0','A real zero return must remain zero');
 await page.getByLabel('Search coins',{exact:true}).fill('nothing-matches');assert.equal(await nodes.count(),0);
 assert.ok((await map.textContent()).includes('No coins match'));
 await page.getByLabel('Search coins',{exact:true}).fill('');
 await page.setViewportSize({width:390,height:844});
 await page.waitForTimeout(150);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Mobile page must not overflow');
 assert.deepEqual(errors,[]);
 console.log('Interactive bubbles: motion/pause, drag, keyboard details, periods, sizing, persistent watchlist, range, reduced motion, fallback, mobile and no extra fetches passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
