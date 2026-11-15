// Restored branch UI with fixture feeds only; no production requests or trades.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await page.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  const replies={
   '/api/auth/me':{id:'fixture',name:'Owner',role:'super_admin'},
   '/api/notifications':[],
   '/api/v1/trading/config':{entitlements:{tier:'ultimate',scanners:true,chartLimit:4}},
   '/api/v1/stocks/heatmap':{provider:'Fixture',feed:'fixture',sectors:[{sector:'Technology',stocks:[{symbol:'AAPL',price:100,volume:1000,change_pct:2}]}]},
   '/api/v1/intelligence/opportunities':{results:[]},
   '/api/v1/intelligence/health':{sources:[]},
  };
  return route.fulfill({status:path in replies?200:404,json:replies[path]||{detail:'Fixture endpoint unavailable'}});
 });
 await page.goto(BASE+'/');
 await page.getByRole('heading',{name:'KAOS TRADING BOT',exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()),'46 65% 52%');
 await page.goto(BASE+'/dashboard/stock-heatmap');
 await page.getByRole('heading',{name:'US stocks & ETFs by daily dollar volume'}).waitFor();
 assert.ok(await page.locator('[data-testid=stock-market-heatmap] svg circle').count()>0);
 assert.equal(await page.getByRole('button',{name:'Bubbles',exact:true}).getAttribute('aria-pressed'),'true');
 const background=await page.locator('.kaos-member-sidebar').evaluate(el=>getComputedStyle(el).backgroundImage);
 assert.ok(background.includes('25, 19, 12'),background);
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('Restored homepage, gold member theme, bubble heat map and mobile layout passed.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
