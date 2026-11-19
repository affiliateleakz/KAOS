// Read-only owner dashboard; all account/provider state is mocked.
const {chromium}=require('../../apps/web/node_modules/playwright');const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL,browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});const writes=[],errors=[];let role='super_admin';page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{
  const q=route.request(),u=new URL(q.url());if(!q.url().startsWith(BASE+'/'))return route.abort();
  if(!u.pathname.startsWith('/api/'))return route.continue();
  if(q.method()!=='GET')writes.push(u.pathname);
  if(u.pathname==='/api/auth/me')return route.fulfill({json:{id:'owner-fixture',role}});
  if(u.pathname==='/api/admin/launch/readiness')return route.fulfill({json:{checkedAt:'2026-11-17T00:00:00Z',stripeMode:'live',notice:'Read-only configuration evidence. Nothing is activated.',checks:[{id:'checkout',title:'Membership checkout',state:'blocked',detail:'Validation hosting blocks billing.',action:'Finish sandbox verification.',href:'/admin/commerce'},{id:'mail',title:'Password recovery email',state:'configured_unverified',detail:'Delivery has not been verified.',action:'Test recovery on your account.',href:'/admin/launch'}],recentProcessedWebhookEvidence:[],externalChecks:['Verify signed webhook delivery and renewals.'],launchCertified:false,activationPerformed:false}});
  return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
 });
 await page.goto(BASE+'/admin/launch');await page.getByRole('heading',{name:'Launch status',exact:true}).waitFor();await page.getByText('No processed webhook evidence found.',{exact:true}).waitFor();
 assert.ok((await page.getByTestId('launch-readiness').textContent()).includes('blocked'));
 await page.getByRole('button',{name:'Refresh launch status',exact:true}).click();
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
 role='admin';await page.reload();await page.waitForURL(BASE+'/dashboard');assert.equal(await page.getByTestId('launch-readiness').count(),0);
 console.log('Launch status: owner-only route, honest blocked/unverified states, no writes and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
