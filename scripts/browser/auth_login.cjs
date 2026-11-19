const BASE=process.env.KAOS_WEB_PREVIEW_URL;
if(!BASE)throw Error('Run through scripts/browser/run.cjs');
const { chromium }=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN || undefined,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext();
 const requests=[]; let success=false;
 await context.route('**/*',route=>route.request().url().startsWith(BASE+'/')?route.continue():route.abort());
 // Support both the configured public API and the same-origin development proxy.
 await context.route('**/api/**',async route=>{
  const request=route.request(), url=new URL(request.url());
  if(request.method()==='OPTIONS') return route.fulfill({status:204,headers:{'access-control-allow-origin':BASE+'','access-control-allow-credentials':'true','access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'content-type'}});
  if(url.pathname==='/api/auth/login'){
   requests.push(request.postDataJSON());
   return route.fulfill({status:success?200:401,json:success?{id:'test-user',role:'user',email:'test@example.com'}:{detail:'Invalid email or password'}});
  }
  return route.fulfill({status:401,json:{detail:'Not authenticated'}});
 });
 await context.route('https://accounts.google.com/gsi/client',route=>route.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize(){},renderButton(target,options){const button=document.createElement('button');button.textContent='Continue with Google';button.style.cssText='height:40px;border:1px solid #445166;border-radius:6px;color:white;background:#101820;max-width:100%;width:'+options.width+'px';target.replaceChildren(button);}}}};`}));
 const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [width,height,name] of [[1440,1000,'desktop'],[390,844,'mobile'],[320,740,'small-mobile']]){
  await page.setViewportSize({width,height});await page.goto(BASE+'/login');
  await page.getByTestId('login-email-input').waitFor();await page.getByText('Continue with Google',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,name+' overflow');
  assert.equal(await page.getByLabel('Email address',{exact:true}).count(),1);
 }
 await page.getByTestId('login-email-input').fill('test@example.com');await page.getByTestId('login-password-input').fill('test-password');
 await page.getByTestId('login-submit-button').click();await page.getByRole('alert').filter({hasText:'Invalid email or password'}).waitFor();
 assert.deepEqual(requests[0],{email:'test@example.com',password:'test-password'});
 success=true;await page.getByTestId('login-submit-button').click();await page.waitForURL('**/dashboard');
 assert.deepEqual(errors,[]);console.log('Desktop/mobile layout, labels, Google sizing, login errors and successful navigation passed (mock API/provider).');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
