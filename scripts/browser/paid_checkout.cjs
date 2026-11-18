// Fresh browser checkout fixtures only. No real Stripe session, payment or account.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL;
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 for(const scenario of ['email','google','signedin','login','disabled','retry']){
  const context=await browser.newContext();const page=await context.newPage({viewport:{width:1280,height:900}});
  let account=scenario==='signedin'?{id:'existing',role:'user',membership_status:'EXPIRED'}:null;
  const requests=[],errors=[],visited=[];let enabled=scenario!=='disabled',checkoutCalls=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('framenavigated',frame=>{if(frame===page.mainFrame())visited.push(frame.url());});
  const plan=scenario==='google'?'ultimate_yearly':'pro';
  const plans=[{id:'free',tier:'free',name:'Free',amount:0,currency:'usd',entitlements:{botAccess:true,chartLimit:1,deviceLimit:1}},
   {id:'pro',tier:'pro',name:'Pro',amount:2995,currency:'usd',interval:'month',entitlements:{botAccess:true,chartLimit:4,deviceLimit:3}},
   {id:'ultimate_yearly',tier:'ultimate',name:'Ultimate',amount:99595,currency:'usd',interval:'year',entitlements:{botAccess:true,chartLimit:4,deviceLimit:5}}];
  await context.route('**/*',route=>{
   const q=route.request(),u=new URL(q.url()),p=u.pathname;
   if(u.hostname==='checkout.stripe.com')return route.fulfill({contentType:'text/html',body:'<h1>Stripe payment fixture</h1>'});
   if(q.url()==='https://accounts.google.com/gsi/client')return route.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize({callback}){window.googleFixture=callback},renderButton(target){const b=document.createElement('button');b.textContent='Continue with Google';b.onclick=()=>window.googleFixture({credential:'google-fixture'});target.replaceChildren(b)}}}};`});
   if(u.origin!==new URL(BASE).origin)return route.abort();
   if(!p.startsWith('/api/'))return route.continue();
   requests.push({path:p,method:q.method(),body:q.method()==='POST'?q.postDataJSON():null});
   if(p==='/api/auth/me')return route.fulfill(account?{json:account}:{status:401,json:{detail:'Not signed in'}});
   if(p==='/api/billing/memberships')return route.fulfill({json:{plans,checkoutEnabled:enabled,affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]},affiliateEnrollmentEnabled:true,payoutsEnabled:false}});
   if(p==='/api/aff/track')return route.fulfill({json:{ok:true}});
   if(['/api/auth/register','/api/auth/google/credential','/api/auth/login'].includes(p)){
    account={id:'customer-fixture',role:'user',membership_status:'EXPIRED'};return route.fulfill({json:account});
   }
   if(p==='/api/billing/checkout'){
    checkoutCalls++;
    if(scenario==='retry'&&checkoutCalls===1)return route.fulfill({status:503,json:{detail:'Fixture temporary payment outage'}});
    assert.equal(q.postDataJSON().plan_id,plan);
    return route.fulfill({json:{checkout_url:'https://checkout.stripe.com/c/pay/cs_fixture',session_id:'cs_fixture'}});
   }
   return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
  });
  await page.goto(BASE+'/?ref=KAOS-REF&utm_source=checkout-test');
  if(plan.endsWith('_yearly'))await page.getByRole('group',{name:'Billing period'}).getByRole('button',{name:'Yearly',exact:true}).click();
  await page.getByTestId('home-plan-'+plan).getByRole('link',{name:'Choose '+(plan==='pro'?'Pro':'Ultimate'),exact:true}).click();
  await page.waitForURL('**/checkout?**');
  if(scenario==='disabled'){
   await page.getByTestId('paid-checkout-unavailable').waitFor();
   assert.equal(await page.getByTestId('register-email-input').count(),0);
   assert.equal(requests.filter(r=>r.path==='/api/auth/register').length,0);
   assert.equal(checkoutCalls,0);
   await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  }else{
   if(!account){
    await page.getByTestId('registration-plan-summary').waitFor();
    assert.equal(new URL(page.url()).searchParams.get('ref'),'KAOS-REF');
    if(scenario==='google')await page.getByRole('button',{name:'Continue with Google',exact:true}).click();
    else if(scenario==='login'){
     await page.getByRole('link',{name:'Sign in',exact:true}).click();
     await page.waitForURL('**/login?**');assert.equal(new URL(page.url()).searchParams.get('plan'),plan);
     await page.getByTestId('login-email-input').fill('existing@example.com');await page.getByTestId('login-password-input').fill('fixture-password');await page.getByTestId('login-submit-button').click();
    }else{
     await page.getByTestId('register-name-input').fill('New buyer');await page.getByTestId('register-email-input').fill('buyer@example.com');await page.getByTestId('register-password-input').fill('fixture-password');await page.getByTestId('register-submit-button').click();
    }
   }
   if(scenario==='retry'){
    await page.getByRole('alert').getByText('Fixture temporary payment outage',{exact:true}).waitFor();
    assert.equal(new URL(page.url()).pathname,'/checkout');
    assert.equal(requests.filter(r=>r.path==='/api/auth/register').length,1);
    await page.getByRole('button',{name:'Retry secure checkout',exact:true}).click();
   }
   await page.waitForURL('https://checkout.stripe.com/**');await page.getByRole('heading',{name:'Stripe payment fixture'}).waitFor();
   assert.equal(checkoutCalls,scenario==='retry'?2:1);
   assert.equal(account.membership_status,'EXPIRED','Opening Checkout is not paid membership activation');
   assert.equal(visited.some(url=>new URL(url).pathname.startsWith('/dashboard')),false);
   if(['signedin','login'].includes(scenario))assert.equal(requests.filter(r=>r.path==='/api/auth/register').length,0);
   const signup=requests.find(r=>['/api/auth/register','/api/auth/google/credential'].includes(r.path));
   if(signup){assert.equal(signup.body.planId,plan);assert.equal(signup.body.refCode,'KAOS-REF');}
  }
  assert.deepEqual(errors,[]);await context.close();
 }
 console.log('Paid homepage checkout: new email/Google buyers, existing sessions, login plan retention, annual/referral retention, disabled-before-signup, retry without duplicate account and no dashboard detour passed. Stripe is mocked.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
