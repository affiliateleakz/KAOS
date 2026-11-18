// Local fixtures only: no Stripe payments, mail, or real accounts.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL,browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{for(const scenario of ['email','annual','signedin','login','disabled','retry','complete']){
  const context=await browser.newContext(),page=await context.newPage({viewport:{width:1280,height:900}});
  let account=scenario==='signedin'?{id:'existing',role:'user',membership_status:'EXPIRED'}:null;
  const requests=[],errors=[],visited=[];let calls=0;
  const plan=scenario==='annual'?'ultimate_yearly':'pro';
  const plans=[{id:'free',tier:'free',name:'Free',amount:0,currency:'usd',entitlements:{botAccess:true,chartLimit:1,deviceLimit:1}},
   {id:'pro',tier:'pro',name:'Pro',amount:2995,currency:'usd',interval:'month',entitlements:{botAccess:true,chartLimit:4,deviceLimit:3}},
   {id:'ultimate_yearly',tier:'ultimate',name:'Ultimate',amount:99595,currency:'usd',interval:'year',entitlements:{botAccess:true,chartLimit:4,deviceLimit:5}}];
  page.on('pageerror',e=>errors.push(e.message));page.on('framenavigated',f=>{if(f===page.mainFrame())visited.push(f.url());});
  await context.route('**/*',route=>{
   const q=route.request(),u=new URL(q.url()),p=u.pathname;
   if(u.hostname==='checkout.stripe.com')return route.fulfill({contentType:'text/html',body:'<h1>Stripe payment fixture</h1>'});
   if(u.origin!==new URL(BASE).origin)return route.abort();
   if(!p.startsWith('/api/'))return route.continue();
   requests.push({path:p,body:q.method()==='POST'?q.postDataJSON():null});
   if(p==='/api/auth/me')return route.fulfill(account?{json:account}:{status:401,json:{detail:'Not signed in'}});
   if(p==='/api/billing/memberships')return route.fulfill({json:{plans,checkoutEnabled:scenario!=='disabled',guestCheckoutEnabled:true,affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]}}});
   if(p==='/api/aff/track')return route.fulfill({json:{ok:true}});
   if(p==='/api/auth/login'){account={id:'existing',role:'user'};return route.fulfill({json:account});}
   if(p==='/api/billing/guest-intent'){
    assert.equal(q.postDataJSON().plan_id,plan);assert.equal(q.postDataJSON().email,'buyer@example.com');
    if(scenario==='login')return route.fulfill({status:409,json:{detail:{code:'SIGN_IN_REQUIRED',message:'Sign in to continue'}}});
    return route.fulfill({json:{ready:true}});
   }
   if(['/api/billing/guest-checkout','/api/billing/checkout'].includes(p)){
    calls++;if(scenario==='retry'&&calls===1)return route.fulfill({status:503,json:{detail:'Fixture temporary outage'}});
    if(p.endsWith('/checkout'))assert.equal(q.postDataJSON().plan_id,plan);
    return route.fulfill({json:{checkout_url:'https://checkout.stripe.com/c/pay/fixture',session_id:'cs_fixture'}});
   }
   if(p==='/api/billing/guest-status/cs_fixture')return route.fulfill({json:{state:'active',setupRequired:true,emailSent:true,receiptEmail:'buyer@example.com'}});
   return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
  });
  if(scenario==='complete'){
   await page.goto(BASE+'/payment/complete?session_id=cs_fixture');await page.getByRole('heading',{name:'Payment confirmed'}).waitFor();
   await page.getByText('Finish account setup using the secure link sent to buyer@example.com.',{exact:false}).waitFor();
   assert.equal(await page.locator('input[type=password]').count(),0);assert.equal(calls,0);
  }else{
   await page.goto(BASE+'/?ref=KAOS-REF&utm_source=checkout-test');
   if(plan.endsWith('_yearly'))await page.getByRole('group',{name:'Billing period'}).getByRole('button',{name:'Yearly',exact:true}).click();
   await page.getByTestId('home-plan-'+plan).getByRole('link',{name:'Choose '+(plan==='pro'?'Pro':'Ultimate'),exact:true}).click();
   await page.waitForURL('**/checkout?**');
   if(scenario==='disabled'){
    await page.getByTestId('paid-checkout-unavailable').waitFor();assert.equal(calls,0);assert.equal(await page.locator('input').count(),0);
   }else{
    if(!account){
     await page.getByTestId('guest-checkout').waitFor();assert.equal(await page.locator('input[type=password]').count(),0);
     assert.equal(new URL(page.url()).searchParams.get('ref'),'KAOS-REF');
     await page.getByTestId('checkout-name').fill('Buyer');await page.getByTestId('checkout-email').fill('buyer@example.com');await page.getByRole('button',{name:'Continue to secure payment',exact:true}).click();
     if(scenario==='login'){
      await page.getByRole('link',{name:'Sign in to continue this membership'}).click();await page.waitForURL('**/login?**');
      assert.equal(new URL(page.url()).searchParams.get('plan'),plan);
      await page.getByTestId('login-email-input').fill('buyer@example.com');await page.getByTestId('login-password-input').fill('fixture-password');await page.getByTestId('login-submit-button').click();
     }
     if(scenario==='retry'){await page.getByRole('alert').getByText('Fixture temporary outage',{exact:true}).waitFor();await page.getByRole('button',{name:'Continue to secure payment',exact:true}).click();}
    }
    await page.getByRole('heading',{name:'Stripe payment fixture'}).waitFor();
   }
  }
  assert.equal(requests.filter(r=>r.path==='/api/auth/register').length,0);
  assert.equal(visited.some(u=>new URL(u).pathname.startsWith('/dashboard')),false);assert.deepEqual(errors,[]);
  await context.close();
 }
 console.log('Payment before account creation: email-only monthly/annual Stripe, receipt setup, existing-account sign-in, disabled checkout and retry passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
