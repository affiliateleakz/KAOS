const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL,browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),requests=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const entitlements={botAccess:true,community:true,scanners:true,aiInsights:true,chartLimit:4,deviceLimit:3};
 const plans=[{id:'free',name:'Free',tier:'free',amount:0,entitlements:{}},{id:'pro',name:'Pro',tier:'pro',amount:4495,currency:'usd',interval:'month',entitlements},{id:'ultimate',name:'Ultimate',tier:'ultimate',amount:15995,currency:'usd',interval:'month',entitlements:{...entitlements,pretrainedModels:true,deviceLimit:5}}];
 await page.route('**/*',route=>{
  const q=route.request(),u=new URL(q.url()),p=u.pathname;
  if(u.hostname==='checkout.stripe.com')return route.fulfill({contentType:'text/html',body:'<h1>Stripe trial fixture</h1>'});
  if(u.origin!==new URL(BASE).origin)return route.abort();
  if(!p.startsWith('/api/'))return route.continue();
  requests.push({path:p,data:q.method()==='POST'?q.postDataJSON():null});
  if(p==='/api/auth/me')return route.fulfill({status:401,json:{detail:'Sign in'}});
  if(p==='/api/billing/memberships')return route.fulfill({json:{plans,trial:{days:7,planId:'pro',amount:4495,currency:'usd',interval:'month'},checkoutEnabled:true,guestCheckoutEnabled:true,affiliateRates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]}}});
  if(p==='/api/billing/guest-intent')return route.fulfill({json:{ready:true}});
  if(p==='/api/billing/guest-cancel/cs_trial')return route.fulfill({json:{cancelAtPeriodEnd:true}});
  if(p==='/api/billing/guest-checkout')return route.fulfill({json:{checkout_url:'https://checkout.stripe.com/c/pay/trial-fixture'}});
  if(p==='/api/billing/guest-status/cs_trial')return route.fulfill({json:{state:'active',trial:true,trialEndsAt:'2026-12-01T12:00:00Z',receiptEmail:'buyer@example.com',setupRequired:true,emailSent:true}});
  if(p==='/api/aff/track')return route.fulfill({json:{ok:true}});
  return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
 });
 await page.goto(BASE+'/?ref=OWNER');
 await page.getByTestId('home-plan-free').getByText('Then $44.95 / month unless canceled. Ultimate is a paid upgrade.',{exact:true}).waitFor();
 await page.getByTestId('home-plan-free').getByRole('link',{name:'7-day free trial',exact:true}).click();
 await page.getByTestId('trial-terms').waitFor();assert.equal(new URL(page.url()).searchParams.get('trial'),'1');
 await page.getByTestId('checkout-name').fill('Buyer');await page.getByTestId('checkout-email').fill('buyer@example.com');
 await page.getByLabel('Membership plan').selectOption('ultimate');
 await page.getByText('Stripe will show $159.95 / month and renewal terms before you pay. Only Pro monthly offers a free trial.',{exact:true}).waitFor();
 assert.equal(await page.getByTestId('trial-terms').count(),0);
 await page.getByLabel('Membership plan').selectOption('pro');
 await page.getByTestId('trial-terms').getByText('All Pro features for 7 days. $0 today, then $44.95 / month unless canceled. One trial per customer email.',{exact:true}).waitFor();
 assert.equal(await page.getByTestId('checkout-name').inputValue(),'Buyer');
 assert.equal(await page.locator('input[type=password]').count(),0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.getByRole('button',{name:'Continue to secure payment'}).click();await page.getByRole('heading',{name:'Stripe trial fixture'}).waitFor();
 const intent=requests.find(r=>r.path==='/api/billing/guest-intent').data;
 assert.equal(intent.start_trial,true);assert.equal(intent.plan_id,'pro');assert.equal(intent.name,'Buyer');assert.equal(intent.refCode,'OWNER');assert.equal(intent.amount,undefined);
 assert.equal(requests.some(r=>r.path==='/api/auth/register'),false);
 await page.goto(BASE+'/payment/complete?session_id=cs_trial');await page.getByRole('heading',{name:'Pro trial confirmed'}).waitFor();
 assert.equal(await page.getByText('Your payment was confirmed.',{exact:true}).count(),0);
 await page.getByRole('button',{name:'Cancel trial renewal'}).click();await page.getByRole('status').getByText('Trial cancellation confirmed. It will not renew.',{exact:true}).waitFor();assert.deepEqual(errors,[]);
 console.log('Pro trial: saved prices, name/email, Pro/Ultimate switch, renewal disclosure, no account before Stripe, referral, mobile and honest trial confirmation passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
