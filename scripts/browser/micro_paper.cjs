// Isolated browser fixtures. No real feed, broker, login, or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_EXTENSION_PREVIEW_URL,root=path.resolve(__dirname,'../..');
 const fixture=JSON.parse(fs.readFileSync(root+'/apps/extension/fixtures/micro-paper-parity.json'));
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1000,height:850},acceptDownloads:true});const errors=[],calls=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.permissionRequests=[];window.chrome={permissions:{request:async options=>{window.permissionRequests.push(options);return true;}}};});
 const seconds=fixture.rows.flatMap(b=>Array.from({length:5},(_,i)=>[b.ts+i*1000,String(b.open),String(b.high),String(b.low),String(b.close),'1',b.ts+i*1000+999,'1',1]));
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());if(url.origin===new URL(BASE).origin)return route.continue();
  assert.equal(url.origin,'https://data-api.binance.vision');assert.equal(route.request().method(),'GET');calls.push(url.pathname);
  if(url.pathname==='/api/v3/time')return route.fulfill({json:{serverTime:fixture.rows.at(-1).closeTs}});
  const limit=Number(url.searchParams.get('limit')),end=url.searchParams.get('endTime');
  return route.fulfill({json:seconds.filter(r=>!end||r[0]<=Number(end)).slice(-limit)});
 });
 await page.goto(BASE+'/kaos-micro-paper.html');assert.equal(await page.getByRole('button',{name:'Start live paper feed'}).isDisabled(),true);assert.equal(calls.length,0);
 await page.locator('#model-file').setInputFiles(root+'/downloads/KAOS-Micro-Reversion-Paper-Model.json');
 await page.getByText('Experimental model loaded locally',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Start live paper feed'}).click();
 await page.getByText('Live paper observation started.',{exact:false}).waitFor();
 assert.deepEqual(calls,['/api/v3/time','/api/v3/klines','/api/v3/klines']);
 assert.equal(await page.locator('#results tr').count(),0,'Warmup must not invent retrospective forward trades');
 assert.equal(await page.evaluate(()=>permissionRequests.length),1);
 await page.getByRole('button',{name:'Stop',exact:true}).click();
 await page.locator('summary').click();
 await page.locator('#candles-file').setInputFiles({name:'BTCUSDT_5s.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({markets:{BTCUSDT:fixture.rows}}))});
 await page.getByText('Historical paper replay complete.',{exact:false}).waitFor();
 assert.ok(await page.locator('#results tr').count()>0);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export paper results'}).click();const file=await download;
 const exported=JSON.parse(fs.readFileSync(await file.path()));assert.equal(exported.executionEnabled,false);assert.equal(exported.mode,'historical-replay');assert.equal(exported.adverseEntryBps,1);assert.ok(exported.results.every(r=>r.paper));
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);console.log('Paper lab: explicit model import, permission on Start only, no warmup trades, local replay/export, adverse-fill defaults, stopped feed and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
