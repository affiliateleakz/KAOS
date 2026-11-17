const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});let vault=false,saveBody;
 const providers=['stripe','paypal','nowpayments'].map(id=>({id,name:{stripe:'Stripe',paypal:'PayPal',nowpayments:'NOWPayments'}[id],description:'Fixture provider setup',dashboard:'https://example.invalid/',mode:'sandbox',paymentsSelected:false,payoutsSelected:false,cryptoAsset:'usdttrc20',fields:[{name:'client_secret',label:'Client secret',environmentVariable:'FIXTURE_SECRET',configured:false,source:'not configured'}],paymentsLive:false,payoutsLive:false}));
 await page.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await page.route('**/api/**',route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  if(path==='/api/auth/me')return route.fulfill({json:{id:'owner-fixture',role:'super_admin'}});
  if(path==='/api/admin/commerce/providers')return route.fulfill({json:{stripeReadiness:{mode:'test',configurationReady:true,checkoutEnabled:false,note:'Login-validation hosting blocks billing and webhook delivery.'},vaultReady:vault,providers,activationNote:'Setup only. Money movement is disabled.'}});
  if(path==='/api/admin/commerce/vault/initialize'){vault=true;return route.fulfill({json:{vaultReady:true}});}
  if(path==='/api/admin/commerce/providers/stripe'&&request.method()==='PUT'){assert.deepEqual(request.postDataJSON().credentials,{});return route.fulfill({json:providers[0]});}
  if(path==='/api/admin/commerce/providers/paypal'&&request.method()==='PUT'){
   saveBody=request.postDataJSON();Object.assign(providers[1],{...saveBody,credentials:undefined});providers[1].fields[0].configured=true;providers[1].fields[0].source='encrypted storage';
   return route.fulfill({json:providers[1]});
  }
  if(path==='/api/admin/commerce/providers/paypal/test')return route.fulfill({json:{ok:true,message:'PayPal API credentials accepted. Payouts are not live.'}});
  return route.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
 });
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(BASE+'/admin/commerce');await page.getByTestId('provider-paypal').waitFor();
 assert.ok((await page.getByTestId('stripe-readiness').textContent()).includes('Checkout: disabled'));
 assert.equal(await page.getByLabel('PayPal Client secret',{exact:true}).getAttribute('type'),'password');
 assert.equal(await page.getByLabel('PayPal Client secret',{exact:true}).isDisabled(),true);
 await page.getByRole('button',{name:'Initialize secure vault'}).click();
 await page.getByRole('button',{name:'Initialize secure vault'}).waitFor({state:'detached'});
 const paypal=page.getByTestId('provider-paypal');await page.getByLabel('PayPal Client secret',{exact:true}).fill('fixture-private-value');
 const refreshed=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/admin/commerce/providers'&&response.request().method()==='GET');
 await page.getByTestId('provider-stripe').getByRole('button',{name:'Save setup',exact:true}).click();await refreshed;
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.getByLabel('PayPal Client secret',{exact:true}).inputValue(),'fixture-private-value','Another provider refresh must preserve an unsaved credential');
 await paypal.getByLabel('Select for affiliate payouts').check();
 assert.equal(await paypal.getByRole('button',{name:'Check API connection'}).isDisabled(),true);
 await paypal.getByRole('button',{name:'Save setup'}).click();
 await paypal.getByText('Settings saved.',{exact:false}).waitFor();
 assert.equal(saveBody.credentials.client_secret,'fixture-private-value');assert.equal(saveBody.payoutsSelected,true);
 assert.equal(await page.getByLabel('PayPal Client secret',{exact:true}).inputValue(),'');
 await paypal.getByRole('button',{name:'Check API connection'}).click();await paypal.getByText('PayPal API credentials accepted.',{exact:false}).waitFor();
 assert.equal(await page.getByTestId('provider-nowpayments').getByLabel('Crypto asset and network').inputValue(),'usdttrc20');
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.equal(await page.getByText('Setup only · not live',{exact:true}).count(),3);
 const stripe=page.getByTestId('provider-stripe');await stripe.getByLabel('Stripe environment',{exact:true}).selectOption('live');await stripe.getByText('Sandbox and live credentials are separate.',{exact:false}).waitFor();assert.equal(await stripe.getByRole('button',{name:'Check API connection',exact:true}).isDisabled(),true);
 assert.deepEqual(errors,[]);console.log('Admin provider setup: vault initialization, masked credentials, save-before-check, PayPal selection, crypto network and mobile layout passed.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
