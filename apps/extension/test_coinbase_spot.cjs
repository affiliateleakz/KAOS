const {test}=require('node:test');
const assert=require('node:assert/strict');
const spot=require('./kaos-coinbase-spot.js');
const end=1800000000000;
function history(){return Array.from({length:100},(_,i)=>[(end-100*60000+i*60000)/1000,100+i,102+i,101+i,101.5+i,10]);}
test('spot strategy uses closed contiguous one-minute candles only',()=>{
 const rows=spot.candles([...history(),[end/1000,1,9999,1,9999,10]],end);
 assert.equal(rows.length,100);assert.equal(rows.at(-1).ts,end-60000);
 const broken=history();broken.splice(50,1);
 assert.throws(()=>spot.candles(broken,end),/gap/);
 assert.throws(()=>spot.candles(history(),end+180000),/stale/);
});
test('spot quote refuses crossed, stale and nonnumeric prices',()=>{
 assert.equal(spot.quote({bid:'100',ask:'101',time:new Date(end).toISOString()},end).bid,100);
 for(const raw of [{bid:102,ask:101},{bid:'bad',ask:101},{bid:100,ask:101,time:new Date(end-20000).toISOString()}])
  assert.throws(()=>spot.quote({time:new Date(end).toISOString(),...raw},end));
});
test('flat history has no spot buy; a trend breakout can buy',()=>{
 const flat=history().map(r=>[r[0],99,101,100,100,10]);
 assert.equal(spot.signal(spot.candles(flat,end)).direction,'WAIT');
 const trend=history();trend.at(-1)[2]=220;trend.at(-1)[4]=219;
 assert.equal(spot.signal(spot.candles(trend,end)).direction,'BUY');
});
