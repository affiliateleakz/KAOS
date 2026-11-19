const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({acceptDownloads:true});let active=false,activations=0;const paths=[];
 await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 await context.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;paths.push(path);
  if(path==='/api/auth/me')return route.fulfill({json:{id:'fixture',role:'user',email:'fixture@example.com'}});
  if(path==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{tier:'free',scanners:false}}});
  if(path==='/api/notifications'||path==='/api/affiliate/marketing')return route.fulfill({json:[]});
  if(path==='/api/affiliate/program')return route.fulfill({json:{enrollmentEnabled:true,payoutsEnabled:false,holdDays:30,tier:'free',rates:{free:[10,0,0],pro:[30,15,0],ultimate:[50,25,5]}}});
  if(path==='/api/affiliate/overview')return route.fulfill({json:active?{active:true,referralLink:'https://tradingwithkaos.com/register?ref=KAOS-FIXTURE',clicks:0,signups:0,payingReferrals:0,pending:0}:{active:false}});
  if(path==='/api/affiliate/activate'){active=true;activations++;return route.fulfill({json:{status:'active'}});}
  if(path==='/api/affiliate/ledger')return route.fulfill({json:{tier:'free',note:'Preview only',balance:{pending:'0',available:'0',reversed:'0',paid:'0'},entries:[]}});
  if(path==='/api/affiliate/connect/status')return route.fulfill({json:{configured:false,transfersEnabled:false}});
  return route.fulfill({status:404,json:{detail:'Fixture endpoint unavailable'}});
 });
 const page=await context.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(BASE+'/dashboard/affiliate');await page.getByTestId('affiliate-activate-button').waitFor();
 await page.getByRole('button',{name:'Create my referral link'}).click();
 await page.getByTestId('affiliate-link').waitFor();assert.equal(activations,1);
 if(process.env.KAOS_CAPTURE_DIR)await page.screenshot({path:process.env.KAOS_CAPTURE_DIR+'/affiliate-hub-preview.png'});
 assert.equal(await page.getByTestId('affiliate-link').inputValue(),'https://tradingwithkaos.com/register?ref=KAOS-FIXTURE');
 const email=await page.getByRole('textbox',{name:'Introduce your audience to KAOS'}).inputValue();
 assert.match(email,/ref=KAOS-FIXTURE/);assert.match(email,/Disclosure/);
 for(const type of ['Social','Community','Email']){await page.getByRole('button',{name:type,exact:true}).click();assert.ok(await page.getByRole('textbox').count()>1);}
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download banner',exact:true}).first().click();
 const download=await downloadPromise;assert.equal(download.suggestedFilename(),'kaos-1200x628.png');
 const png=fs.readFileSync(await download.path());assert.equal(png.readUInt32BE(16),1200);assert.equal(png.readUInt32BE(20),628);
 await page.getByTestId('affiliate-connect').waitFor();assert.equal(await page.getByRole('button',{name:'Continue to Stripe'}).isDisabled(),true);
 assert.ok(await page.getByText('Payouts are not live yet.',{exact:false}).count()>0);
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.ok(!paths.some(path=>path.includes('/transfer')||path.includes('/checkout')));assert.deepEqual(errors,[]);
 console.log('Affiliate enrollment, personal campaign links, disclosure copy, real PNG download, mobile layout and truthful payout state passed.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
