const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {Context,score,PaperSession}=require('./kaos-micro-paper-core.js');
const model=JSON.parse(fs.readFileSync(path.join(__dirname,'../../research/crypto_strategy_v1/browser_model.json')));
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/micro-paper-parity.json')));
test('browser features and exported trees match Python/XGBoost on real candles',()=>{
 const ctx=new Context(),expected=new Map(fixture.expected.map(e=>[e.index,e]));let checks=0;
 for(let i=0;i<fixture.rows.length;i++){ctx.push(fixture.rows[i]);if(expected.has(i)){const e=expected.get(i);e.vector.forEach((v,j)=>assert.ok(Math.abs(ctx.vector[j]-v)<Math.max(1e-4,Math.abs(v)*1e-5),'feature '+j));const p=score(model,ctx.vector);assert.ok(Math.abs(p.probUp-e.probUp)<1e-6);assert.equal(p.direction,e.direction);assert.equal(p.executionEnabled,false);checks++;}}
 assert.ok(checks>20);assert.ok(fixture.expected.some(e=>e.direction!=='HOLD'));
});
function alwaysBuy(){return {...model,base:3,trees:[],symbols:['BTCUSDT']};}
function bars(count=350){return Array.from({length:count},(_,i)=>({ts:1791244800000+i*5000,closeTs:1791244800000+(i+1)*5000,open:100+i*.001,high:101+i*.001,low:99+i*.001,close:100.01+i*.001}));}
test('paper positions enter on next open, settle exactly 15s later and do not overlap',()=>{
 const session=new PaperSession(alwaysBuy(),'BTCUSDT',{adverseBps:1});const rows=bars();rows.forEach(r=>session.step(r));assert.ok(session.results.length>1);
 for(const r of session.results){assert.equal(r.exitTs-r.entryTs,15000);const bar=rows.find(b=>b.ts===r.entryTs);assert.equal(r.entry,bar.open*1.0001);assert.equal(r.outcome,'LOSS');assert.equal(r.paper,true);}
 for(let i=1;i<session.results.length;i++)assert.ok(session.results[i].entryTs>=session.results[i-1].exitTs);
 assert.equal(session.summary().executionEnabled,false);
});
test('gaps reset warmup and cancel unresolved positions instead of inventing settlements',()=>{
 const session=new PaperSession(alwaysBuy(),'BTCUSDT');const rows=bars(321);rows.forEach(r=>session.step(r));assert.ok(session.open);
 const gap={...rows.at(-1),ts:rows.at(-1).ts+15000,closeTs:rows.at(-1).ts+20000};session.step(gap);assert.equal(session.summary().cancelled,1);assert.equal(session.results.length,0);assert.equal(session.summary().warmup,1);assert.equal(session.lastDecision.direction,'HOLD');
});
test('warmup history alone cannot create live paper trades',()=>{
 const session=new PaperSession(alwaysBuy(),'BTCUSDT');bars().forEach(r=>session.context.push(r));assert.equal(session.results.length,0);assert.equal(session.open,null);assert.equal(session.pending,null);
});
test('invalid or duplicated bars and unsupported markets are rejected',()=>{
 assert.throws(()=>new PaperSession(model,'EURUSD_otc'));const ctx=new Context(),row=bars(1)[0];ctx.push(row);assert.throws(()=>ctx.push(row));assert.throws(()=>new Context().push({...row,closeTs:row.ts+4000}));
});
test('public second aggregation excludes partial and empty buckets',()=>{
 const {aggregateSeconds}=require('./kaos-micro-paper-core.js'),ts=1791244800000;
 const rows=Array.from({length:5},(_,i)=>[ts+i*1000,'100','101','99','100.5','1',ts+i*1000+999,'1',1]);
 assert.equal(aggregateSeconds(rows,ts+5000).length,1);
 assert.equal(aggregateSeconds(rows.slice(0,4),ts+5000).length,0);
 assert.equal(aggregateSeconds(rows.map(r=>{const c=[...r];c[8]=0;return c;}),ts+5000).length,0);
 assert.equal(aggregateSeconds(rows,ts+4000).length,0);
});
