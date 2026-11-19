const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
const plans=[{id:'free',name:'Free',amount:0,currency:'usd',interval:null,tier:'free',entitlements:{chartLimit:1,deviceLimit:1,botAccess:true,community:true}},
 {id:'pro',name:'Pro',amount:4900,currency:'usd',interval:'month',tier:'pro',entitlements:{chartLimit:4,deviceLimit:3,botAccess:true,community:true,scanners:true,aiInsights:true,cloudStrategies:true}},
 {id:'ultimate',name:'Ultimate',amount:14900,currency:'usd',interval:'month',tier:'ultimate',entitlements:{chartLimit:4,deviceLimit:5,botAccess:true,community:true,scanners:true,aiInsights:true,cloudStrategies:true,premiumTools:true,modes:['STRATEGY','AI']}}];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 for(const [planId,google] of [['pro',false],['free',true]]){
  const context=await browser.newContext();let payload,checkoutCalls=0,tracks=0;const errors=[];
  await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
  await context.route('https://accounts.google.com/gsi/client',route=>route.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize({callback}){window.fixtureGoogleCallback=callback},renderButton(target){const b=document.createElement('button');b.textContent='Continue with Google';b.onclick=()=>window.fixtureGoogleCallback({credential:'fixture-google-token'});target.replaceChildren(b)}}}};`}));
  await context.route('**/api/**',route=>{
   const request=route.request(),path=new URL(request.url()).pathname;
   if(path==='/api/auth/me')return route.fulfill({status:401,json:{detail:'Not signed in'}});
   if(path==='/api/billing/memberships')return route.fulfill({json:{plans,affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]},affiliateEnrollmentEnabled:true,payoutsEnabled:false,checkoutEnabled:false}});
   if(path==='/api/aff/track'){tracks++;return route.fulfill({json:{ok:true}});}
   if(path==='/api/auth/register'||path==='/api/auth/google/credential'){payload=request.postDataJSON();return route.fulfill({json:{id:'fixture',role:'user',email:'new@example.com',requested_membership_plan:payload.planId,membership_status:'EXPIRED'}});}
   if(path==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{chartLimit:1,tier:'free'}}});
   if(path==='/api/notifications')return route.fulfill({json:[]});
   if(path==='/api/billing/plans')return route.fulfill({json:plans.filter(p=>p.id!=='free')});
   if(path==='/api/billing/availability')return route.fulfill({json:{checkoutEnabled:false,mode:'unconfigured'}});
   if(path==='/api/billing/checkout'){checkoutCalls++;return route.fulfill({status:503,json:{detail:'Unavailable'}});}
   return route.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
  });
  const page=await context.newPage({viewport:{width:1280,height:900}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE+'/register?ref=KAOS-REF&utm_source=campaign');await page.getByTestId('membership-selection').waitFor();await page.getByTestId('choose-membership-pro').waitFor();
  assert.equal(await page.getByTestId('register-email-input').count(),0);
  if(process.env.KAOS_CAPTURE_DIR&&!google)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/memberships-preview.png'});
  assert.ok((await page.getByTestId('membership-card-ultimate').textContent()).includes('50%'));
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.getByTestId('choose-membership-'+planId).click();
  await page.getByTestId('paid-checkout-unavailable').waitFor();
  const current=new URL(page.url());assert.equal(current.searchParams.get('ref'),'KAOS-REF');assert.equal(current.searchParams.get('utm_source'),'campaign');
  assert.equal(current.searchParams.get('plan'),'pro');if(planId==='free')assert.equal(current.searchParams.get('trial'),'1');
  assert.equal(payload,undefined);assert.equal(checkoutCalls,0);assert.equal(await page.locator('input[type=password]').count(),0);
  assert.deepEqual(errors,[]);await context.close();
 }
 console.log('Membership/trial selection, mobile comparison, referral retention and disabled checkout before account creation passed.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
