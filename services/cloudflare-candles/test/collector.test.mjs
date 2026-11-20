import test from "node:test";
import assert from "node:assert/strict";
import {validateMarkets,closedBars,storeBars,objectKey,runScheduled} from "../src/index.mjs";

const market={symbol:"AAPL",asset_class:"stock",seconds:60};
const START=1761955200000;
const sample=(i)=>({ts:START+i*60000,open:100,high:101,low:99,close:100.2,volume:50});
const source="alpaca_iex";
function bucket(){
  const mem=new Map();const puts=[];
  return {
    mem,puts,
    async get(key){return mem.has(key)?{json:async()=>JSON.parse(mem.get(key))}:null;},
    async put(key,value){mem.set(key,value);puts.push(key);}
  };
}

test("market symbols validated and duplicates rejected",()=>{
  assert.equal(validateMarkets([market])[0].symbol,"AAPL");
  assert.throws(()=>validateMarkets([market,market]),/Duplicate/);
  assert.throws(()=>validateMarkets([{...market,symbol:"../../"}]),/Invalid/);
  assert.throws(()=>validateMarkets(Array(21).fill(market)),/1–20/);
});

test("only complete, valid candles archived",()=>{
  const records=[sample(0),sample(1),{...sample(2),high:1}];
  const out=closedBars(market,source,records,START+60000);
  assert.equal(out.length,1);assert.equal(out[0].ts,START);
});
test("R2 day partition merges without rewriting identical backfills",async()=>{
  const b=bucket();
  const rows=closedBars(market,source,[sample(0),sample(1)],START+3*60000);
  const first=await storeBars(b,rows);
  const second=await storeBars(b,rows);
  assert.equal(first.newBars,2);assert.equal(second.newBars,0);
  assert.equal(b.puts.length,1);
  const row=JSON.parse(b.mem.get(objectKey(rows[0])));
  assert.equal(row.candles.length,2);
});
test("different real bar values cannot overwrite past immutable archive",async()=>{
  const b=bucket();
  const rows=closedBars(market,source,[sample(0)],START+3*60000);
  await storeBars(b,rows);
  await assert.rejects(()=>storeBars(b,[{...rows[0],close:100.4}]),/revision/);
});
test("worker isolates failed feeds and keeps permitted market running",async()=>{
  const b=bucket();
  const env={CANDLE_ARCHIVE:b,MARKETS_JSON:JSON.stringify([market,
    {symbol:"BTC-USD",asset_class:"crypto",seconds:60}])};
  const fetcher=async m=>{
    if(m.asset_class==="crypto")throw Error("provider_unavailable");
    return {source,bars:[sample(0),sample(1)]};
  };
  const r=await runScheduled(env,{nowMs:START+3*60000,fetcher});
  assert.equal(r.ok,1);assert.equal(r.errors,1);
  assert.equal(b.puts.length,1);
  assert.equal(r.results[0].mirror.status,"disabled");
});
test("R2 never exposes or serves saved candles over public fetch",async()=>{
  const worker=(await import("../src/index.mjs")).default;
  const r=await worker.fetch();
  assert.equal(r.status,404);
});
