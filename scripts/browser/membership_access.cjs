// Real website routes with fixture accounts only; no checkout or production calls.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext();let mode='free',feedCalls=0;
 await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await context.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/auth/me')return route.fulfill({json:{id:'fixture',role:mode==='owner'?'super_admin':'user',email:'fixture@example.com'}});
  if(path==='/api/notifications')return route.fulfill({json:[]});
  if(path==='/api/billing/plans')return route.fulfill({json:[{id:'pro',name:'Pro',amount:4900,interval:'month',features:['Four charts']},{id:'ultimate',name:'Ultimate',amount:14900,interval:'month',features:['Premium tools']}]});
  if(path==='/api/billing/availability')return route.fulfill({json:{checkoutEnabled:false,mode:'unconfigured'}});
  if(path==='/api/v1/trading/config')return route.fulfill({status:mode==='error'?503:200,json:mode==='error'?{detail:'Unavailable'}:{entitlements:{tier:mode==='free'?'free':'ultimate',scanners:mode==='owner',chartLimit:mode==='owner'?4:1}}});
  if(path==='/api/v1/stocks/heatmap'){feedCalls++;return route.fulfill({json:{sectors:[],provider:'Alpaca',feed:'iex'}});}
  return route.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
 });
 const page=await context.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(BASE+'/dashboard/stock-heatmap');
 await page.getByTestId('membership-upgrade').waitFor();assert.equal(feedCalls,0);
 assert.equal(await page.getByTestId('compare-memberships').getAttribute('href'),'/dashboard/subscription');
 assert.ok(await page.getByRole('heading',{name:'Unlock Stock Heat Map'}).isVisible());
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.getByTestId('compare-memberships').click();await page.getByTestId('subscribe-pro').waitFor();
 assert.equal(await page.getByTestId('subscribe-pro').isDisabled(),true);
 assert.equal(await page.getByTestId('subscribe-ultimate').isDisabled(),true);
 assert.ok(await page.getByText('$49',{exact:false}).isVisible());
 assert.equal(await page.getByText('4242',{exact:false}).count(),0);
 mode='owner';await page.goto(BASE+'/dashboard/stock-heatmap');await page.getByTestId('stock-market-heatmap').waitFor();
 assert.equal(await page.getByTestId('membership-upgrade').count(),0);
 await page.getByText('Provider: Alpaca',{exact:false}).waitFor();assert.equal(feedCalls,1);
 mode='error';await page.reload();await page.getByRole('heading',{name:'We couldn’t check your access'}).waitFor();
 assert.equal(await page.getByTestId('membership-upgrade').count(),0);assert.equal(feedCalls,1);
 mode='free';await page.getByRole('button',{name:'Try again',exact:true}).click();await page.getByTestId('membership-upgrade').waitFor();
 assert.deepEqual(errors,[]);console.log('Membership upgrade: direct-route lock, no restricted feed request, mobile layout, owner access, outage distinction and retry passed.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
