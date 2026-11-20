import test from "node:test";
import assert from "node:assert/strict";
import {normalizeTvBars} from "./tradingview_api_adapter.mjs";
const make=(i)=>({time:1761955200+i*60,open:100,high:101,low:99,close:100.5,volume:50});
const config={symbol:"NASDAQ:AAPL",timeframe:"1",nowSeconds:1761955200+15*60};
test("qualified symbols and correct complete candle handling",()=>{
  const r=normalizeTvBars(Array.from({length:10},(_,i)=>make(i)),config);
  assert.equal(r.complete_bars,10);
  assert.equal(r.ai_training_approved,false);
  assert.equal(r.gaps,0);
  assert.equal(r.source,"tradingview_community_unofficial");
});
test("exclude forming bar",()=>{
  const r=normalizeTvBars([make(0),make(14)],config);
  assert.equal(r.complete_bars,1);
});
test("reject invalid candle and duplicate time",()=>{
  assert.throws(()=>normalizeTvBars([{...make(0),high:1}],config),/Inconsistent/);
  assert.throws(()=>normalizeTvBars([make(0),make(0)],config),/Duplicate/);
});
test("flag price gaps without inventing bars",()=>{
  const r=normalizeTvBars([make(0),make(2)],config);
  assert.equal(r.gaps,1);assert.equal(r.complete_bars,2);
});
test("sub-minute timeframes supported only when source really supplies them",()=>{
  const r=normalizeTvBars([{...make(0),time:1761955200}],{
    symbol:"BINANCE:BTCUSDT",timeframe:"5S",nowSeconds:1761955210});
  assert.equal(r.seconds,5);
});
test("require exchange-qualified symbol",()=>{
  assert.throws(()=>normalizeTvBars([make(0)],{...config,symbol:"AAPL"}),/Exchange-qualified/);
});
