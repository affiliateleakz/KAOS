// All prices/providers/accounts below are local fixtures. No real checkout.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL;
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[],checkout=[];let registered=null;
 page.on('pageerror',e=>errors.push(e.message));
 const make=(tier,interval,amount)=>({id:tier+(interval==='year'?'_yearly':''),tier,name:tier==='pro'?'Pro':'Ultimate',amount,currency:'usd',interval,lookup_key:'membership_'+tier+'_'+(interval==='year'?'yearly':'monthly'),recommended:tier==='ultimate'&&interval==='month',entitlements:{botAccess:true,community:true,chartLimit:4,deviceLimit:tier==='pro'?3:5,scanners:true,aiInsights:true,cloudStrategies:true,premiumTools:tier==='ultimate',modes:['STRATEGY']}});
 const paid=[make('pro','month',2995),make('ultimate','month',9995),make('pro','year',29995),make('ultimate','year',99595)];
 const plans=[{id:'free',tier:'free',name:'Free',amount:0,currency:'usd',entitlements:{botAccess:true,community:true,chartLimit:1,deviceLimit:1}},...paid];
 await page.route('**/*',r=>r.request().url().startsWith(BASE+'/')?r.continue():r.abort());
 await page.route('**/api/**',r=>{const req=r.request(),p=new URL(req.url()).pathname;
 if(p==='/api/auth/me')return r.fulfill(registered?{json:registered}:{status:401,json:{detail:'Not signed in'}});
 if(p==='/api/billing/memberships')return r.fulfill({json:{plans,affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]},affiliateHoldDays:30,affiliateEnrollmentEnabled:true,payoutsEnabled:false,checkoutEnabled:true}});
 if(p==='/api/billing/plans')return r.fulfill({json:paid});
 if(p==='/api/billing/availability')return r.fulfill({json:{checkoutEnabled:true,mode:'test'}});
 if(p==='/api/auth/register'){const data=req.postDataJSON();registered={id:'fixture',role:'user',name:'Member',requested_membership_plan:data.planId,membership_status:'EXPIRED'};return r.fulfill({json:registered});}
 if(p==='/api/billing/checkout'){checkout.push(req.postDataJSON());return r.fulfill({status:503,json:{detail:'Fixture: no payment provider contacted'}});}
 if(p==='/api/notifications')return r.fulfill({json:[]});
 if(p==='/api/aff/track')return r.fulfill({json:{ok:true}});
 if(p==='/api/v1/trading/config')return r.fulfill({json:{entitlements:{tier:'free',chartLimit:1}}});
 return r.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
 });
 await page.goto(BASE+'/');
 await page.getByTestId('home-plan-pro').getByText('$29.95',{exact:false}).waitFor();
 await page.getByTestId('home-plan-ultimate').getByText('$99.95',{exact:false}).waitFor();
 await page.getByTestId('home-plan-ultimate').getByText('Recommended · Ultimate monthly',{exact:true}).waitFor();
 await page.getByRole('group',{name:'Billing period'}).getByRole('button',{name:'Yearly',exact:true}).click();
 await page.getByTestId('home-plan-pro_yearly').getByText('$299.95',{exact:false}).waitFor();
 await page.getByTestId('home-plan-ultimate_yearly').getByText('$995.95',{exact:false}).waitFor();
 assert.equal(await page.getByTestId('home-plan-free').count(),1);
 assert.equal(await page.locator('.kh-plans article').count(),3);
 assert.equal(await page.getByText('Recommended · Ultimate monthly',{exact:true}).count(),0);
 await page.getByTestId('home-plan-pro_yearly').getByText('Save $59.45 per year compared with monthly billing.',{exact:true}).waitFor();
 await page.getByTestId('home-plan-ultimate_yearly').getByText('Save $203.45 per year compared with monthly billing.',{exact:true}).waitFor();
 await page.getByTestId('home-direct-examples-free').getByText('Pro payment → $30.00',{exact:true}).waitFor();
 await page.getByTestId('home-direct-examples-ultimate_yearly').getByText('Ultimate payment → $497.98',{exact:true}).waitFor();
 await page.getByRole('group',{name:'Billing period'}).getByRole('button',{name:'Monthly',exact:true}).click();
 await page.getByTestId('home-plan-pro').getByText('$29.95',{exact:false}).waitFor();
 assert.equal(checkout.length,0);
 await page.goto(BASE+'/register?ref=KAOS-REF');
 await page.getByTestId('choose-membership-pro').waitFor();
 await page.getByRole('group',{name:'Billing period'}).getByRole('button',{name:'Yearly',exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.getByTestId('choose-membership-pro_yearly').click();
 await page.getByTestId('registration-plan-summary').getByText('Pro · $299.95 / year',{exact:true}).waitFor();
 assert.equal(new URL(page.url()).searchParams.get('ref'),'KAOS-REF');
 await page.getByRole('link',{name:'Change membership',exact:true}).click();
 await page.getByTestId('choose-membership-pro_yearly').waitFor();
 await page.getByTestId('choose-membership-pro_yearly').click();
 await page.getByTestId('register-name-input').fill('Member');await page.getByTestId('register-email-input').fill('member@example.com');await page.getByTestId('register-password-input').fill('fixture-password');await page.getByTestId('register-submit-button').click();
 await page.waitForURL('**/dashboard/subscription?plan=pro_yearly');
 await page.getByTestId('subscribe-pro_yearly').waitFor();
 assert.equal(registered.requested_membership_plan,'pro_yearly');assert.equal(registered.membership_status,'EXPIRED');assert.equal(checkout.length,0);
 await page.getByTestId('subscribe-pro_yearly').click();
 await page.waitForFunction(()=>document.body.textContent.includes('Fixture: no payment provider contacted'));
 assert.equal(checkout.length,1);assert.equal(checkout[0].lookup_key,'membership_pro_yearly');
 assert.deepEqual(errors,[]);
 console.log('Monthly/yearly pricing, annual savings, monthly recommendation, affiliate annual amounts, Free persistence, mobile signup and explicit annual checkout payload passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
