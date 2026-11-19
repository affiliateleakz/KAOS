// Member Coinbase setup; API fixtures only, no provider credentials or real orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL;
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[],writes=[];let saved=false,fail=false,marketCalls=0;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
   const q=route.request(),u=new URL(q.url()),p=u.pathname;
   if(u.origin!==new URL(BASE).origin)return route.abort();
   if(!p.startsWith('/api/'))return route.continue();
   if(q.method()!=='GET')writes.push(p);
   if(p==='/api/auth/me')return route.fulfill({json:{id:'member-fixture',role:'user',membership_status:'ACTIVE'}});
   if(p==='/api/notifications')return route.fulfill({json:[]});
   if(p==='/api/v1/trading/config')return route.fulfill({json:{entitlements:{tier:'pro',botAccess:true,chartLimit:4}}});
   if(p==='/api/v1/broker-selection')return route.fulfill({json:{broker:'coinbase',live_order_authorized:false}});
   if(p==='/api/v1/broker-connections')return route.fulfill({json:{connections:saved?[{broker:'coinbase',saved:true,verified:true,key_hint:'1234',verified_at:'2026-11-18T00:00:00Z'}]:[]}});
   if(p==='/api/v1/broker-connections/coinbase'){
    if(q.method()==='PUT'){
     if(fail)return route.fulfill({status:502,json:{detail:'Coinbase verification failed'}});
     assert.equal(q.postDataJSON().key_name,'');saved=true;
    }else if(q.method()==='DELETE')saved=false;
    else throw Error('Unexpected connection method');
    return route.fulfill({json:{saved,live_order_authorized:false}});
   }
   if(p==='/api/v1/broker-connections/coinbase/products'){
    marketCalls++;assert.equal(q.method(),'GET');
    return route.fulfill({json:{products:[{product_id:'BTC-USD'},{product_id:'ETH-USD'}],partial_catalog:true,live_order_authorized:false}});
   }
   return route.fulfill({status:404,json:{detail:'Fixture unavailable'}});
  });
  await page.goto(BASE+'/dashboard/brokers');
  await page.getByRole('heading',{name:'KAOS Broker Connections',exact:true}).waitFor();
  assert.equal(marketCalls,0);
  await page.getByLabel('Private key',{exact:true}).fill('credentials-json-fixture');
  await page.getByRole('button',{name:'Verify & save Coinbase',exact:true}).click();
  await page.getByText('Coinbase read access verified and encrypted credentials saved. Live trading remains disabled.',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('Private key',{exact:true}).inputValue(),'');
  await page.getByRole('button',{name:'Check Coinbase markets',exact:true}).click();
  await page.getByTestId('coinbase-markets').getByText('BTC-USD, ETH-USD',{exact:true}).waitFor();
  assert.equal(marketCalls,1);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  fail=true;await page.getByLabel('Private key',{exact:true}).fill('bad-credentials-fixture');
  await page.getByRole('button',{name:'Verify & save Coinbase',exact:true}).click();
  await page.getByRole('alert').getByText('Coinbase connection failed: Coinbase verification failed',{exact:true}).waitFor();
  assert.equal(saved,true);
  page.on('dialog',d=>d.accept());
  await page.getByRole('button',{name:'Disconnect',exact:true}).click();
  await page.getByText('Coinbase disconnected.',{exact:true}).waitFor();
  assert.equal(await page.getByTestId('coinbase-markets').count(),0);
  assert.ok(writes.every(p=>p==='/api/v1/broker-connections/coinbase'));
  assert.deepEqual(errors,[]);
  console.log('Coinbase setup: JSON credentials, cleared key, explicit read-only market check, failed update, disconnect and mobile layout passed. No order requests.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
