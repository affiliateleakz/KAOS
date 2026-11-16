// Admin-only settings fixtures. No live changes or payment providers.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL;
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});const writes=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const plan=(id,amount,devices)=>({id,tier:id,name:id==='pro'?'Pro':'Ultimate',amount,currency:'usd',interval:'month',deviceLimit:devices,entitlements:{botAccess:true,community:true,chartLimit:4,deviceLimit:devices,scanners:true,aiInsights:true,cloudStrategies:true,premiumTools:id==='ultimate',modes:id==='pro'?['STRATEGY']:['STRATEGY','AI','STRATEGY_AI']}});
 const settings={branding:{productName:'KAOS'},affiliate:{},plans:[{id:'monthly',name:'Old monthly',amount:1900,currency:'usd',interval:'month'}],planDefaults:[plan('pro',4900,3),plan('ultimate',14900,5)],freePlan:{id:'free',tier:'free',name:'Free',amount:0,entitlements:{chartLimit:1,deviceLimit:1,botAccess:true,community:true}},affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]}};
 await page.route('**/*',r=>r.request().url().startsWith(BASE+'/')?r.continue():r.abort());
 await page.route('**/api/**',r=>{const p=new URL(r.request().url()).pathname;
 if(p==='/api/auth/me')return r.fulfill({json:{id:'owner',name:'Owner',role:'super_admin'}});
 if(p==='/api/notifications')return r.fulfill({json:[]});
 if(p==='/api/admin/settings'){if(r.request().method()==='POST'){writes.push(r.request().postDataJSON());return r.fulfill({json:{ok:true}});}return r.fulfill({json:settings});}
 return r.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
 });
 await page.goto(BASE+'/admin/settings');
 await page.getByTestId('admin-plan-free').getByText('$0',{exact:false}).waitFor();
 assert.equal(writes.length,0);
 await page.getByRole('button',{name:'Use current KAOS plans',exact:true}).click();
 await page.getByTestId('admin-plan-pro').getByText('$49.00',{exact:false}).waitFor();
 await page.getByTestId('admin-plan-ultimate').getByText('$149.00',{exact:false}).waitFor();
 assert.equal(writes.length,0,'Loading defaults must not save live settings');
 await page.getByTestId('admin-plan-pro').getByText('4 broker chart slots · 3 devices',{exact:true}).waitFor();
 await page.getByTestId('admin-plan-free').getByText('Affiliate commissions: Level 1: 10%',{exact:true}).waitFor();
 await page.getByLabel('pro price in cents',{exact:true}).fill('49.5');
 assert.equal(await page.getByTestId('save-plans-button').isDisabled(),true);
 await page.getByLabel('pro price in cents',{exact:true}).fill('5900');
 await page.getByTestId('admin-plan-pro').getByText('$59.00',{exact:false}).waitFor();
 await page.getByTestId('save-plans-button').click();
 await page.getByText('No unsaved changes.',{exact:false}).waitFor();
 assert.equal(writes.length,1);assert.equal(writes[0].key,'plans');
 const saved=writes[0].value.value;
 assert.deepEqual(saved.map(p=>p.id),['pro','ultimate']);assert.equal(saved[0].amount,5900);assert.equal(saved[0].entitlements.chartLimit,4);assert.equal(saved[1].amount,14900);
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('Membership settings: Free, current tier defaults, configurable prices, four-chart limits, affiliate rates, explicit Save and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
