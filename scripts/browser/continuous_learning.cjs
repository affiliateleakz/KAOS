// New learning/offerings UX with local fixtures only; no real training, releases or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const BASE=process.env.KAOS_WEB_PREVIEW_URL;
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[],requests=[];let role='user',jobs=[];
 page.on('pageerror',e=>errors.push(e.message));
 const status=()=>({policy:'kaos-service-learning-v1',sharedLearningRequired:true,notice:'De-identified settled trade features train personal, shared and owner models. Credentials, payments and balances are excluded.',personalTraining:true,pretrainedAccess:false,personalSamples:12,personalModels:[],sharedModels:[],jobs,worker:{running:false,configured:false},executionEnabled:false,minimumSamples:500});
 await page.route('**/*',r=>r.request().url().startsWith(BASE+'/')?r.continue():r.abort());
 await page.route('**/api/**',r=>{const q=r.request(),u=new URL(q.url()),p=u.pathname;
 if(p==='/api/auth/me')return r.fulfill({json:{id:'member',name:'Member',role,membership_status:'ACTIVE',membership_plan:'pro'}});
 if(p==='/api/notifications')return r.fulfill({json:[]});
 if(p==='/api/v1/trading/config')return r.fulfill({json:{entitlements:{tier:'pro',scanners:true,aiInsights:true,aiTraining:true,pretrainedModels:false,chartLimit:4}}});
 if(p==='/api/v1/ai/training/status')return r.fulfill({json:status()});
 if(p==='/api/v1/ai/training/train'){requests.push(q.postDataJSON());jobs=[{id:'job',scope:requests.at(-1).scope,state:'queued'}];return r.fulfill({json:{jobId:'job',state:'queued',executionEnabled:false}});}
 if(p==='/api/admin/ai/continuous/status')return r.fulfill({json:{worker:{running:false,phase:'Not deployed'},models:[],notice:'Required service learning'}});
 if(p==='/api/admin/ai/continuous/owner/train'){requests.push({owner:true});return r.fulfill({json:{state:'queued'}});}
 if(p==='/api/v1/intelligence/offerings')return r.fulfill({json:u.searchParams.get('kind')==='ipo'?{state:'complete',message:'Example scheduled IPO calendar',items:[{name:'Example Issuer',symbol:'TEST',date:'2026-12-01',dateType:'scheduled, subject to change',source:'Fixture source',sourceUrl:'https://example.com',priceLow:10,priceHigh:12,currency:'USD'}],risks:['Research only. No execution.']}:{state:'no_confirmed_data',message:'Primary sources are required.',items:[],risks:[]}});
 if(p==='/api/admin/ai/models')return r.fulfill({json:[]});
 if(p==='/api/admin/ai/learning')return r.fulfill({json:{totalSamples:0,realSamples:0,paperSamples:0,consentedUsers:0,datasets:[],trainingRuns:[]}});
 return r.fulfill({status:404,json:{detail:'Fixture unavailable'}});
 });
 await page.goto(BASE+'/dashboard/kaos-ai');
 await page.getByTestId('personal-ai-workspace').waitFor();
 await page.getByText('Private training · starts untrained',{exact:true}).waitFor();
 await page.getByText('Not running / heartbeat unavailable',{exact:true}).waitFor();
 assert.equal(await page.getByRole('switch').count(),0);
 assert.equal(await page.getByRole('button',{name:'Queue personal training',exact:true}).isEnabled(),true);
 await page.getByRole('button',{name:'Queue personal training',exact:true}).click();
 await page.getByText('pocket_option:binary:5s:20s:real · queued',{exact:true}).waitFor();
 assert.deepEqual(requests,[{scope:'pocket_option:binary:5s:20s:real'}]);
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.goto(BASE+'/dashboard/opportunities');
 await page.getByRole('navigation',{name:'Radar sections'}).getByRole('button',{name:'IPOs & ICOs',exact:true}).click();
 await page.getByRole('heading',{name:'TEST · Example Issuer',exact:true}).waitFor();
 await page.getByRole('button',{name:'Crypto ICOs',exact:true}).click();
 await page.getByText('No confirmed ICO entries are available. KAOS does not fill this list with guessed offerings.',{exact:true}).waitFor();
 assert.equal(await page.getByText('Owner: add a sourced ICO entry',{exact:true}).count(),0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 role='super_admin';await page.goto(BASE+'/admin/kaos-ai');
 await page.getByTestId('continuous-training-admin').waitFor();
 await page.getByText('Worker: Not running / deployment pending · Last phase: Not deployed',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Queue my owner model',exact:true}).click();
 assert.equal(requests.at(-1).owner,true);assert.deepEqual(errors,[]);
 console.log('Private untrained AI, required learning disclosure/no opt-in, queued training, truthful worker status, sourced IPO/ICO states, owner queue and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
