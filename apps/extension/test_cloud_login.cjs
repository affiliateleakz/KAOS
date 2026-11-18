const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
function cloud(responses) {
  const storage = {}, calls = [];
  const context = {module: {exports: {}}, crypto: {randomUUID: () => 'device-test'},
    setTimeout, clearTimeout, AbortController,
    chrome: {runtime: {getManifest: () => ({version:"1.7.26",oauth2:{client_id:"fixture-client"}})}, storage: {local: {
      get: (keys, cb) => cb(storage), set: (obj, cb) => {Object.assign(storage, obj); cb();}
    }}},
    fetch: async (url, opts) => {
      calls.push({url, opts});
      const next = responses.shift();
      if (next instanceof Error) throw next;
      assert.ok(next, 'unexpected request');
      return new Response(next.raw ?? JSON.stringify(next.body), {status: next.status});
    }};
  vm.runInNewContext(fs.readFileSync(__dirname + '/kaos-cloud.js', 'utf8'), context);
  return {api: context.module.exports, storage, calls, context};
}
test('legacy 404 reports incompatibility without resending credentials or storing a session', async () => {
  const c = cloud([{status:404, body:{detail:'Not found'}},
    {status:200, body:{runtime:'native-wsgi'}}]);
  await assert.rejects(c.api.login('member@example.com', 'secret'), e => e.kind === 'INCOMPATIBLE_SERVER');
  assert.equal(c.calls.length, 2);
  assert.equal(c.calls[1].opts.method, 'GET');
  assert.equal(c.storage.kaos_tokens, undefined);
});
test('401 never retries credentials or probes another login endpoint', async () => {
  const c = cloud([{status:401, body:{detail:'Invalid credentials'}}]);
  await assert.rejects(c.api.login('member@example.com', 'wrong'), e => e.kind === 'BAD_CREDENTIALS');
  assert.equal(c.calls.length, 1);
});
test('v1 bearer login stores supported tokens and preserves device registration sequencing', async () => {
  const c = cloud([{status:200, body:{accessToken:'access', refreshToken:'refresh', user:{id:'u1'}}}]);
  await c.api.login('member@example.com', 'secret');
  assert.equal(c.storage.kaos_tokens.accessToken, 'access');
  assert.equal(c.storage.installId, 'device-test');
  assert.equal(c.calls.length, 1);
});
test('cookie-only legacy response cannot establish an extension session', async () => {
  const c = cloud([{status:200, body:{user:{id:'u1'}}}]);
  await assert.rejects(c.api.login('member@example.com', 'secret'), /access token/);
  assert.equal(c.storage.kaos_tokens, undefined);
});

for (const detail of ['Device limit reached (1)', 'Device access revoked', 'Bot access is not authorized']) {
  test('device registration preserves server reason: ' + detail, async () => {
    const c = cloud([{status:403, body:{detail}}]);
    await assert.rejects(c.api.registerDevice(), e => e.message === detail && e.httpStatus === 403);
    assert.equal(c.calls.length, 1);
  });
}
test('registration outage is reported as an API failure rather than device revocation', async () => {
  const c = cloud([{status:503, body:{detail:'Login validation mode: this operation is disabled'}}]);
  await assert.rejects(c.api.registerDevice(), e => e.kind === 'API_ERROR' && e.httpStatus === 503);
});
test('startup carries the exact registration refusal into the blocked screen', async () => {
  const c = cloud([{status:200, body:{accessToken:'access', user:{id:'u1'}}},
    {status:403, body:{detail:'Device limit reached (1)'}}]);
  await c.api.login('member@example.com', 'secret');
  const state = await c.api.startup();
  assert.equal(state.step, 'BLOCKED');
  assert.equal(state.detail, 'Device limit reached (1)');
});
test('periodic session check validates the server license without device writes or optional config requests',async()=>{
 const c=cloud([{status:200,body:{accessToken:'access'}},
  {status:200,body:{license:{authorized:true},entitlements:{chartLimit:4},user:{id:'u1'}}}]);
 await c.api.login('member@example.com','secret');
 const result=await c.api.sessionStatus();
 assert.equal(result.status,'CONNECTED');assert.equal(c.calls.length,2);
 assert.ok(c.calls[1].url.endsWith('/extension/me'));assert.equal(c.calls[1].opts.method,'GET');
});
test('periodic check preserves revoked-device denial and does not retry registration',async()=>{
 const c=cloud([{status:200,body:{accessToken:'access'}},{status:403,body:{detail:'Device access revoked'}}]);
 await c.api.login('member@example.com','secret');const result=await c.api.sessionStatus();
 assert.equal(result.step,'BLOCKED');assert.equal(result.detail,'Device access revoked');assert.equal(c.calls.length,2);
});
test('periodic server failure is offline rather than an expired password session',async()=>{
 const c=cloud([{status:200,body:{accessToken:'access'}},{status:503,body:{detail:'Temporarily unavailable'}}]);
 await c.api.login('member@example.com','secret');const result=await c.api.sessionStatus();
 assert.equal(result.step,'OFFLINE');assert.equal(result.httpStatus,503);
});

test('hosting bot challenge is never treated as a successful API health check', async()=>{
 const c=cloud([{status:200,raw:'<title>Bot Verification</title>'},{status:200,raw:'<form id="lsrecaptcha-form">'}]);
 const result=await c.api.health();assert.equal(result.ok,false);assert.match(result.error,/hosting firewall/);
});
test('password login detects an HTTP 200 hosting challenge without saving a session',async()=>{
 const c=cloud([{status:200,raw:'<title>Bot Verification</title>'}]);
 await assert.rejects(c.api.login('member@example.com','secret'),e=>e.kind==='HOSTING_VERIFICATION');
 assert.equal(c.storage.kaos_tokens,undefined);
});
test('Google exchange detects hosting HTML without accepting it as a login',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'fixture-client'}},{status:200,raw:'<title>Bot Verification</title>'}]);
 c.context.chrome.identity={getAuthToken:async()=>({token:'fixture-google-token'})};
 await assert.rejects(c.api.googleLogin(),e=>e.kind==='HOSTING_VERIFICATION');
 assert.equal(c.storage.kaos_tokens,undefined);
});
test('Google exchange stores only returned KAOS tokens, never the Google token',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'fixture-client'}},{status:200,body:{accessToken:'kaos-access',refreshToken:'kaos-refresh',user:{id:'u1'}}}]);
 c.context.chrome.identity={getAuthToken:async()=>({token:'fixture-google-token'})};
 await c.api.googleLogin();
 assert.equal(c.storage.kaos_tokens.accessToken,'kaos-access');
 assert.ok(!JSON.stringify(c.storage).includes('fixture-google-token'));
 assert.equal(c.calls[1].url,'https://api.tradingwithkaos.com/api/v1/extension/google/access-token');
});

test('unconfigured Google login fails before opening OAuth or storing tokens',async()=>{
 const c=cloud([{status:200,body:{configured:false,client_id:null}}]);let opened=false;
 c.context.chrome.identity={getAuthToken:async()=>{opened=true;return 'google';}};
 await assert.rejects(c.api.googleLogin(),/not configured/);assert.equal(opened,false);assert.equal(c.storage.kaos_tokens,undefined);
});
test('mismatched OAuth clients fail before sending Google tokens',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'other-client'}}]);
 c.context.chrome.identity={getAuthToken:async()=>{throw Error('must not run');}};
 await assert.rejects(c.api.googleLogin(),/different Google OAuth clients/);assert.equal(c.calls.length,1);
});
test('Google sign-in removes an invalid cached token and retries exactly once',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'fixture-client'}},{status:401,body:{detail:'Invalid Google access token'}},{status:200,body:{accessToken:'kaos-access'}}]);
 const removed=[];let issued=0;
 c.context.chrome.identity={getAuthToken:async()=>({token:'google-'+(++issued)}),removeCachedAuthToken:async({token})=>removed.push(token)};
 await c.api.googleLogin();assert.deepEqual(removed,['google-1']);assert.equal(issued,2);assert.equal(c.storage.kaos_tokens.accessToken,'kaos-access');
});
test('Google rejection after the refresh does not loop or save a session',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'fixture-client'}},{status:401,body:{detail:'Invalid Google access token'}},{status:401,body:{detail:'Invalid Google access token'}}]);
 let issued=0;c.context.chrome.identity={getAuthToken:async()=>({token:'google-'+(++issued)}),removeCachedAuthToken:async()=>{}};
 await assert.rejects(c.api.googleLogin(),/Invalid Google access token/);assert.equal(issued,2);assert.equal(c.storage.kaos_tokens,undefined);
});

test('Google sign-in rejects another extension ID before sending anything',async()=>{
 const c=cloud([]);c.context.chrome.runtime.id='pnbakkallmfhliciobnamffmhclkgofb';
 c.context.chrome.identity={getAuthToken:async()=>{throw Error('must not run');}};
 await assert.rejects(c.api.googleLogin(),/gbobopmnjgeeegniphckfpalhnebapjm/);
 assert.equal(c.calls.length,0);
});
test('Google cancellation leaves email login available and saves no session',async()=>{
 const c=cloud([{status:200,body:{configured:true,client_id:'fixture-client'}}]);
 c.context.chrome.identity={getAuthToken:async()=>{throw Error('The user did not approve access.');}};
 await assert.rejects(c.api.googleLogin(),/cancelled.*email sign-in/);
 assert.equal(c.calls.length,1);assert.equal(c.storage.kaos_tokens,undefined);
});

test('a backend without the diagnostic route can still perform the verified Google exchange',async()=>{
 const c=cloud([{status:404,body:{detail:'Not Found'}},{status:200,body:{accessToken:'verified-kaos-token',user:{id:'u1'}}}]);
 c.context.chrome.runtime.id='gbobopmnjgeeegniphckfpalhnebapjm';
 c.context.chrome.identity={getAuthToken:async()=>({token:'google-fixture'})};
 await c.api.googleLogin();
 assert.equal(c.storage.kaos_tokens.accessToken,'verified-kaos-token');
 assert.equal(c.calls.length,2);
 assert.ok(c.calls[1].url.endsWith('/extension/google/access-token'));
 assert.equal(JSON.parse(c.calls[1].opts.body).access_token,'google-fixture');
});
test('missing diagnostic route never replaces server-side Google verification',async()=>{
 const c=cloud([{status:404,body:{detail:'Not Found'}},{status:401,body:{detail:'Unrecognized Google OAuth client'}}]);
 c.context.chrome.identity={getAuthToken:async()=>({token:'google-fixture'})};
 await assert.rejects(c.api.googleLogin(),/Unrecognized Google OAuth client/);
 assert.equal(c.storage.kaos_tokens,undefined);
});
test('an HTML 404 for the diagnostic route does not prevent a verified Google exchange',async()=>{
 const c=cloud([{status:404,raw:'<h1>Not Found</h1>'},{status:200,body:{accessToken:'verified-kaos-token'}}]);
 c.context.chrome.identity={getAuthToken:async()=>({token:'google-fixture'})};
 await c.api.googleLogin();assert.equal(c.storage.kaos_tokens.accessToken,'verified-kaos-token');
});

function edgeLogin(responses, reply) {
 const c=cloud(responses);
 Object.assign(c.context,{URL,URLSearchParams,navigator:{userAgent:'Mozilla/5.0 Edg/130.0'}});
 c.context.chrome.identity={
  getAuthToken:async()=>{throw Error('Edge must not call Chrome token API');},
  getRedirectURL:path=>'https://gbobopmnjgeeegniphckfpalhnebapjm.chromiumapp.org/'+path,
  launchWebAuthFlow:async({url})=>reply(new URL(url))
 };
 return c;
}
const edgeConfig={status:200,body:{configured:true,client_id:'fixture-client',web_client_id:'web-client'}};
test('Edge browser OAuth exchanges a state-validated token without storing it',async()=>{
 const c=edgeLogin([edgeConfig,{status:200,body:{accessToken:'kaos-access',user:{id:'u1'}}}],url=>{
  assert.equal(url.searchParams.get('client_id'),'web-client');
  return url.searchParams.get('redirect_uri')+'#'+new URLSearchParams({state:url.searchParams.get('state'),access_token:'edge-google-token',token_type:'Bearer'});
 });
 await c.api.googleLogin();
 assert.equal(JSON.parse(c.calls[1].opts.body).access_token,'edge-google-token');
 assert.equal(c.storage.kaos_tokens.accessToken,'kaos-access');
 assert.ok(!JSON.stringify(c.storage).includes('edge-google-token'));
});
for(const failure of ['state','redirect','cancel']) test('Edge rejects '+failure+' before token exchange',async()=>{
 const c=edgeLogin([edgeConfig],url=>{
  if(failure==='cancel')throw Error('cancelled');
  return (failure==='redirect'?'https://attacker.example/google':url.searchParams.get('redirect_uri'))+'#'+new URLSearchParams({state:failure==='state'?'wrong':url.searchParams.get('state'),access_token:'untrusted',token_type:'Bearer'});
 });
 await assert.rejects(c.api.googleLogin());
 assert.equal(c.calls.length,1);assert.equal(c.storage.kaos_tokens,undefined);
});
test('Edge missing web client gives setup instruction without opening OAuth',async()=>{
 const c=edgeLogin([{status:200,body:{configured:true,client_id:'fixture-client'}}],()=>{throw Error('must not open');});
 await assert.rejects(c.api.googleLogin(),/KAOS_GOOGLE_BROWSER_CLIENT_ID/);
 assert.equal(c.storage.kaos_tokens,undefined);
});
