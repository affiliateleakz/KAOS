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
   '/api/billing/memberships':{plans:[{id:'free',tier:'free',name:'Free',amount:0,currency:'usd',entitlements:{botAccess:true,community:true,chartLimit:1,deviceLimit:1}},{id:'pro',tier:'pro',name:'Pro',amount:9900,currency:'usd',interval:'month',entitlements:{botAccess:true,chartLimit:4,deviceLimit:3,community:true,scanners:true,aiInsights:true,cloudStrategies:true,modes:['STRATEGY']}},{id:'ultimate',tier:'ultimate',name:'Ultimate',amount:14900,currency:'usd',interval:'month',entitlements:{botAccess:true,chartLimit:4,deviceLimit:5,community:true,scanners:true,aiInsights:true,cloudStrategies:true,premiumTools:true,modes:['STRATEGY','AI','STRATEGY_AI']}}],affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]},affiliateHoldDays:30,affiliateEnrollmentEnabled:true,payoutsEnabled:false,checkoutEnabled:false},
   '/api/v1/trading/config':{entitlements:{tier:'ultimate',scanners:true,chartLimit:4}},
   '/api/v1/stocks/heatmap':{provider:'Fixture',feed:'fixture',sectors:[{sector:'Technology',stocks:[{symbol:'AAPL',price:100,volume:1000,change_pct:2}]}]},
   '/api/v1/intelligence/opportunities':{results:[]},
   '/api/v1/intelligence/health':{sources:[]},
  };
  return route.fulfill({status:path in replies?200:404,json:replies[path]||{detail:'Fixture endpoint unavailable'}});
 });
 await page.goto(BASE+'/');
 await page.getByRole('heading',{name:'KAOS TRADING BOT',exact:true}).waitFor();
 const artwork=page.locator('.kh-reference-art');
 await artwork.evaluate(img=>img.decode());
 assert.equal(await artwork.getAttribute('src'),'/kaos-approved-hero.png');
 assert.equal(await artwork.evaluate(img=>img.naturalWidth),1671);
 assert.equal(await page.getByRole('navigation',{name:'Homepage navigation',exact:true}).getByRole('link',{name:'Login',exact:true}).getAttribute('href'),'/login');
 assert.equal(await page.getByRole('navigation',{name:'Homepage navigation',exact:true}).getByRole('link',{name:'Get KAOS',exact:true}).getAttribute('href'),'/register');
 assert.equal(await page.locator('.kh-reference-card').count(),3);
 const currentImages=page.getByTestId('homepage-current-product-images');
 assert.equal(await currentImages.locator('img').count(),3);
 assert.equal(await page.getByRole('link',{name:'Download KAOS Bot from the official Chrome Web Store listing',exact:true}).getAttribute('href'),'https://chromewebstore.google.com/detail/gbobopmnjgeeegniphckfpalhnebapjm');
 for(const img of await page.locator('.kh-reference-main img,.kh-reference-card img').all())await img.evaluate(img=>img.decode());
 await currentImages.getByRole('link',{name:'Explore the current KAOS website',exact:true}).click();
 await page.getByRole('tabpanel').getByRole('heading',{name:'Research before you trade',exact:true}).waitFor();
 await page.getByRole('link',{name:'Explore KAOS STRATEGY',exact:true}).click();
 await page.getByRole('tabpanel').getByRole('heading',{name:'Your KAOS Strategy workspace',exact:true}).waitFor();
 await page.getByTestId('home-plan-free').waitFor();
 await page.getByTestId('home-plan-pro').getByText('$99.00',{exact:false}).waitFor();
 await page.getByTestId('homepage-commission-total').getByText('$9.90',{exact:false}).waitFor();
 const comparison=page.getByRole('table',{name:'Membership benefits comparison',exact:true});
 await comparison.getByRole('row',{name:'Broker chart slots 1 4 4',exact:true}).waitFor();
 await comparison.getByRole('row',{name:'Devices 1 3 5',exact:true}).waitFor();
 await comparison.getByRole('row',{name:'Premium tools Not included Not included Included',exact:true}).waitFor();
 await comparison.getByRole('row',{name:'Affiliate Level 1 10% 30% 50%',exact:true}).waitFor();
 await comparison.getByRole('row',{name:'Affiliate Level 2 Not included 15% 25%',exact:true}).waitFor();
 await comparison.getByRole('row',{name:'Affiliate Level 3 Not included Not included 5%',exact:true}).waitFor();
 await page.getByTestId('home-direct-examples-free').getByText('Pro payment → $9.90',{exact:true}).waitFor();
 await page.getByTestId('home-direct-examples-ultimate').getByText('Ultimate payment → $74.50',{exact:true}).waitFor();
 await page.getByTestId('homepage-affiliate-payouts').getByText('Commissions have a 30-day hold. Refunds and chargebacks can reverse commissions.',{exact:true}).waitFor();
 await page.getByTestId('homepage-affiliate-payouts').getByText(/Cash payouts are not live yet/).waitFor();

 await page.getByLabel('Your affiliate tier',{exact:true}).selectOption('ultimate');
 await page.getByLabel('Level 2 paid referrals',{exact:true}).fill('1');
 await page.getByTestId('homepage-commission-total').getByText('$74.25',{exact:false}).waitFor();
 for(const tab of await page.getByRole('tab').all()){await tab.click();await page.locator('#product-preview-panel img').scrollIntoViewIfNeeded();await page.locator('#product-preview-panel img').evaluate(img=>img.decode());}
 await page.evaluate(()=>scrollTo(0,0));
 if(process.env.KAOS_CAPTURE_DIR)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/approved-homepage.png'});
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.ok(await page.getByRole('navigation',{name:'Mobile homepage navigation'}).isVisible());
 await page.setViewportSize({width:1280,height:900});

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
