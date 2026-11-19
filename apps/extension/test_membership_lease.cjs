const {test}=require('node:test');const assert=require('node:assert/strict');
const {allowed,fromLicense}=require('./kaos-membership-lease');
test('trial deadline blocks new entries at expiry and fails closed for malformed deadlines',()=>{
 const end='2026-12-01T12:00:00Z',stamp=Date.parse(end);
 assert.equal(allowed(end,stamp-1),true);assert.equal(allowed(end,stamp),false);assert.equal(allowed(end,stamp+1),false);
 assert.equal(allowed('bad-date',stamp),false);
 assert.equal(allowed(fromLicense({membershipStatus:'TRIAL'}),stamp),false);
});
test('confirmed paid access removes trial deadline; legacy access does not acquire a fabricated expiry',()=>{
 assert.equal(fromLicense({membershipStatus:'TRIAL',expiresAt:'2026-12-01T12:00:00Z'}),'2026-12-01T12:00:00Z');
 assert.equal(fromLicense({membershipStatus:'ACTIVE',expiresAt:'2027-01-01T00:00:00Z'}),null);
 assert.equal(allowed(null,Date.now()),true);
});
