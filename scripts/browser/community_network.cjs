// Social fixtures only: no real accounts, messages, scripts or orders.
const {chromium}=require('../../apps/web/node_modules/playwright');
const assert=require('node:assert/strict');
const BASE=process.env.KAOS_WEB_PREVIEW_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||undefined,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:950}}),errors=[];page.on('pageerror',e=>errors.push(e.stack));
 const people=[{id:'alice',username:'alice',displayName:'Alice',name:'Alice',bio:'Building together'},{id:'bob',username:'bob',displayName:'Bob',name:'Bob',bio:'Forex researcher'},{id:'charlie',username:'charlie',displayName:'Charlie',name:'Charlie',bio:'Crypto explorer'}];
 const me={...people[0],role:'user'},following=new Set(),likes=new Set(),comments=[],reports=[],calls=[];
 const posts=[{id:'post_bob',authorId:'bob',kind:'discussion',title:'Trading the London session',body:'How do you confirm your setup?',createdAt:'2026-11-16T12:00:00Z',updatedAt:'2026-11-16T12:00:00Z'},
  {id:'post_charlie',authorId:'charlie',kind:'strategy',title:'Crypto momentum research',body:'Discuss this public strategy.',strategyId:'strategy_public',createdAt:'2026-11-16T11:00:00Z',updatedAt:'2026-11-16T11:00:00Z'}];
 const enrich=post=>({...post,author:people.find(p=>p.id===post.authorId),isFollowing:following.has(post.authorId),liked:likes.has(post.id),likesCount:likes.has(post.id)?1:0,commentsCount:comments.filter(c=>c.postId===post.id).length,canDelete:post.authorId==='alice',strategy:post.strategyId?{id:'strategy_public',name:'Momentum fixture',version:1}:null});
 await page.route('**/*',r=>r.request().url().startsWith(BASE+'/')?r.continue():r.abort());
 await page.route('**/api/**',route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname,method=req.method();calls.push({path,method});
  const ok=value=>route.fulfill({json:value});
  if(path==='/api/auth/me')return ok(me);
  if(path==='/api/notifications')return ok([]);
  if(path==='/api/v1/trading/config')return ok({entitlements:{community:true,tier:'free'}});
  if(path==='/api/community/strategies')return ok([]);
  if(path.startsWith('/api/profiles/')){const person=people.find(p=>p.username===path.split('/').at(-1));return ok({...person,publicStrategies:0,followers:following.has(person.id)?1:0,following:0,isFollowing:following.has(person.id),strategies:[]});}
  if(/^\/api\/users\/[^/]+\/follow$/.test(path)){const id=path.split('/')[3];method==='DELETE'?following.delete(id):following.add(id);return ok({following:following.has(id)});}
  if(path==='/api/community/members'){
   const q=(url.searchParams.get('q')||'').toLowerCase();let items=people.filter(p=>(p.displayName+' '+p.username).toLowerCase().includes(q));
   if(url.searchParams.get('connection')==='followers')items=following.has(url.searchParams.get('username'))?[people[0]]:[];
   if(url.searchParams.get('connection')==='following')items=people.filter(p=>following.has(p.id));
   return ok({items:items.map(p=>({...p,isFollowing:following.has(p.id)})),hasMore:false});
  }
  if(path==='/api/community/posts'){
   if(method==='POST'){const body=req.postDataJSON();const post={...body,id:'post_new',authorId:'alice',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()};posts.unshift(post);return ok(enrich(post));}
   const result=posts.filter(p=>(url.searchParams.get('mode')!=='following'||following.has(p.authorId))&&(!url.searchParams.get('author')||p.authorId===url.searchParams.get('author'))&&(!url.searchParams.get('kind')||url.searchParams.get('kind')==='all'||p.kind===url.searchParams.get('kind')));
   return ok({items:result.map(p=>{const row=enrich(p);delete row.code;return row;}),nextCursor:null});
  }
  const match=path.match(/^\/api\/community\/posts\/([^/]+)(.*)$/);
  if(match){const [_,id,suffix]=match;const post=posts.find(p=>p.id===id);
   if(suffix==='/like'){method==='DELETE'?likes.delete(id):likes.add(id);return ok({liked:likes.has(id)});}
   if(suffix==='/report'){reports.push(req.postDataJSON());return ok({reported:true});}
   if(suffix==='/comments'){
    if(method==='POST'){const c={...req.postDataJSON(),id:'comment_'+comments.length,postId:id,author:people[0],createdAt:new Date().toISOString(),canDelete:true};comments.unshift(c);return ok(c);}
    return ok({items:comments.filter(c=>c.postId===id),nextCursor:null});
   }
   if(method==='PATCH'){Object.assign(post,req.postDataJSON());return ok(enrich(post));}
   if(method==='DELETE'){posts.splice(posts.indexOf(post),1);return ok({removed:true});}
   return ok(enrich(post));
  }
  return ok({});
 });
 await page.goto(BASE+'/dashboard/community');
 await page.getByRole('heading',{name:'Your trading circle.',exact:true}).waitFor();
 const bob=()=>page.getByRole('article',{name:'Post by bob',exact:true});
 await bob().getByRole('heading',{name:'Trading the London session'}).waitFor();
 assert.equal(await bob().getByRole('button',{name:'Delete post',exact:true}).count(),0);
 await bob().getByRole('button',{name:'Follow',exact:true}).click();
 await bob().getByRole('button',{name:'Following',exact:true}).waitFor();
 await page.getByRole('navigation',{name:'Community sections'}).getByRole('button',{name:'Following',exact:true}).click();
 await bob().waitFor();await page.getByRole('article',{name:'Post by charlie',exact:true}).waitFor({state:'detached'});
 assert.equal(await page.getByRole('article',{name:'Post by charlie',exact:true}).count(),0);
 await bob().getByRole('button',{name:'Like · 0',exact:true}).click();await bob().getByRole('button',{name:'Liked · 1',exact:true}).waitFor();
 await bob().getByRole('button',{name:'Comments · 0',exact:true}).click();
 await bob().getByRole('textbox',{name:'Write a comment',exact:true}).fill('Good question. I wait for a closed candle.');
 await bob().getByRole('button',{name:'Post comment',exact:true}).click();
 await bob().locator('p').filter({hasText:'Good question. I wait for a closed candle.'}).waitFor();
 assert.equal(comments.length,1);
 await bob().getByRole('button',{name:'Reply',exact:true}).click();
 await bob().getByRole('textbox',{name:'Write a comment',exact:true}).fill('And check the higher timeframe.');
 await bob().getByRole('button',{name:'Post comment',exact:true}).click();
 await bob().locator('p').filter({hasText:'And check the higher timeframe.'}).waitFor();assert.equal(comments[0].parentId,'comment_0');
 await bob().getByRole('button',{name:'Report',exact:true}).click();
 await bob().getByRole('combobox',{name:'Report reason'}).selectOption('Misleading content');
 await bob().getByRole('button',{name:'Send report',exact:true}).click();
 await bob().getByRole('status').filter({hasText:'Report sent to moderators.'}).waitFor();assert.equal(reports.length,1);
 await page.getByRole('navigation',{name:'Community sections'}).getByRole('button',{name:'Feed',exact:true}).click();
 await page.getByRole('combobox',{name:'Post type',exact:true}).selectOption('script');
 await page.getByRole('textbox',{name:'Post title',exact:true}).fill('A script for review');
 await page.getByRole('textbox',{name:'Your community post',exact:true}).fill('This code is shared as text, not executed.');
 await page.getByRole('textbox',{name:'Shared script code',exact:true}).fill('window.__untrustedScriptExecuted = true; <script>alert(1)</script>');
 await page.getByRole('button',{name:'Publish post',exact:true}).click();
 const own=page.getByRole('article',{name:'Post by alice',exact:true});
 await own.getByRole('heading',{name:'A script for review',exact:true}).waitFor();
 await own.getByRole('button',{name:'View script',exact:true}).click();
 await own.locator('pre').waitFor();assert.equal(await page.evaluate(()=>window.__untrustedScriptExecuted),undefined);
 const download=page.waitForEvent('download');await own.getByRole('button',{name:'Download script',exact:true}).click();assert.ok((await download).suggestedFilename().endsWith('.txt'));
 await own.getByRole('button',{name:'Edit post',exact:true}).click();
 await page.getByRole('form',{name:'Edit community post'}).getByRole('textbox',{name:'Your community post',exact:true}).fill('Updated script explanation.');
 await page.getByRole('button',{name:'Save changes',exact:true}).click();await own.getByText('Updated script explanation.',{exact:true}).waitFor();
 await page.getByRole('combobox',{name:'Community post filter'}).selectOption('script');await own.waitFor();await bob().waitFor({state:'detached'});assert.equal(await bob().count(),0);
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Social feed must fit mobile');
 await page.getByRole('navigation',{name:'Community sections'}).getByRole('button',{name:'Members',exact:true}).click();
 await page.getByRole('textbox',{name:'Find community members'}).fill('Charlie');
 await page.getByRole('link',{name:'Charlie',exact:true}).waitFor();
 await page.getByRole('button',{name:'Follow charlie',exact:true}).click();await page.getByRole('button',{name:'Unfollow charlie',exact:true}).waitFor();
 await page.getByRole('link',{name:'Charlie',exact:true}).click();
 await page.getByRole('navigation',{name:'Member profile sections'}).waitFor();
 await page.getByRole('button',{name:'followers',exact:true}).click();await page.getByRole('link',{name:'Alice',exact:true}).waitFor();
 await page.goto(BASE+'/dashboard/following');await bob().waitFor();assert.equal(await page.getByRole('article',{name:'Post by alice',exact:true}).count(),0);
 const before=calls.length;await page.waitForTimeout(1200);assert.equal(calls.length,before,'Feed must not continuously poll shared hosting');
 assert.deepEqual(errors,[]);
 console.log('Member social feed: follow/Following, comments/replies, likes, reports, non-executing script sharing/download/edit, member search, profile connections and mobile layout passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
