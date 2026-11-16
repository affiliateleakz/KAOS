// Offline SR1.1 baseline. Incremental aggregates are checked against the unchanged engine.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const source=fs.readFileSync(path.join(__dirname,'../apps/extension/candidate7b_strategy.js'),'utf8');
const original={window:{}};vm.createContext(original);vm.runInContext(source,original);
const needle='const q5=aggregate(rows,5),q15=aggregate(rows,15),q30=aggregate(rows,30),q60=aggregate(rows,60);';
assert.ok(source.includes(needle));
const cached=`const emaCache=new WeakMap();function cachedEma(rows,p,skip=0){const end=rows.length-skip;if(end<p)return NaN;let cache=emaCache.get(rows);if(!cache){cache=new Map;emaCache.set(rows,cache);}const key=p+':'+skip;let state=cache.get(key);if(!state){let sum=0;for(let i=0;i<p;i++)sum+=rows[i].close;state={count:p,value:sum/p};cache.set(key,state);}const k=2/(p+1);while(state.count<end){state.value+=k*(rows[state.count].close-state.value);state.count++;}return state.value;}`;
const transformed=cached+source.replace(needle,'const [q5,q15,q30,q60]=rows;').replace('ema(q60.map(x=>x.close),9)',"cachedEma(q60,9)").replace('ema(q60.map(x=>x.close),21)',"cachedEma(q60,21)").replace('ema(q15.slice(0,-1).map(x=>x.close),9)',"cachedEma(q15,9,1)");
const fast={window:{}};vm.createContext(fast);vm.runInContext(transformed,fast);
const results={literal_close_markers:{trades:0,wins:0,losses:0,ties:0},next_candle_confirmed:{trades:0,wins:0,losses:0,ties:0}};
let parityChecks=0;
for(const [mode,result] of Object.entries(results)){
 for(const [asset,raw] of input.parts){
  const rows=raw.map(r=>({ts:r[0],open:r[1],high:r[2],low:r[3],close:r[4],closeTs:mode==='literal_close_markers'?input.markers[asset][String(r[0])]:r[0]+5000}));let busy=0,positiveChecks=0;
  const streams=[5,15,30,60].map(sec=>({ms:sec*1000,current:null,closed:[]}));
  for(let i=0;i<rows.length-1;i++){
   const row=rows[i];
   if(row.closeTs>row.ts)for(const s of streams){
    const k=Math.floor(row.ts/s.ms)*s.ms;
    if(!s.current||s.current.ts!==k)s.current={...row,ts:k};
    else Object.assign(s.current,{high:Math.max(s.current.high,row.high),low:Math.min(s.current.low,row.low),close:row.close,closeTs:Math.max(s.current.closeTs,row.closeTs)});
    if(s.current.closeTs>=k+s.ms-1){if(s.closed.at(-1)?.ts===k)s.closed[s.closed.length-1]={...s.current};else s.closed.push({...s.current});}
   }
   const entryTs=row.ts+5000;if(i<299||entryTs<input.start||entryTs>=input.end)continue;
   const signal=fast.window.KAOSCandidate7B.signal(streams.map(s=>s.closed));
   if(i%4000===0||(signal&&positiveChecks<2)){
    const expected=original.window.KAOSCandidate7B.signal(rows.slice(0,i+1));
    assert.equal(JSON.stringify(signal),JSON.stringify(expected),'Incremental baseline must match actual engine');parityChecks++;if(signal)positiveChecks++;
   }
   if(!signal||entryTs<busy)continue;
   const end=i+1+signal.expiry/5;if(end>=rows.length||entryTs+signal.expiry*1000>=input.end)continue;
   const move=rows[end].open-rows[i+1].open;result.trades++;
   if(move===0)result.ties++;else if(move*(signal.dir==='BUY'?1:-1)>0)result.wins++;else result.losses++;
   busy=entryTs+signal.expiry*1000;
  }
 }
 result.win_rate=result.wins/(result.wins+result.losses)||null;result.pnl_at_80pct=Number((result.wins*.8-result.losses).toFixed(4));result.live_approved=false;
}
console.log(JSON.stringify({...results,parity_checks:parityChecks,period:'validation only; no final holdout evaluation'},null,2));
