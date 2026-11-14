const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
function cloud(responses) {
  const storage = {}, calls = [];
  const context = {module: {exports: {}}, crypto: {randomUUID: () => 'device-test'},
    setTimeout, clearTimeout, AbortController,
    chrome: {runtime: {getManifest: () => ({version:"1.7.14"})}, storage: {local: {
      get: (keys, cb) => cb(storage), set: (obj, cb) => {Object.assign(storage, obj); cb();}
    }}},
    fetch: async (url, opts) => {
      calls.push({url, opts});
      const next = responses.shift();
      if (next instanceof Error) throw next;
      assert.ok(next, 'unexpected request');
      return new Response(JSON.stringify(next.body), {status: next.status});
    }};
  vm.runInNewContext(fs.readFileSync(__dirname + '/kaos-cloud.js', 'utf8'), context);
  return {api: context.module.exports, storage, calls};
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
