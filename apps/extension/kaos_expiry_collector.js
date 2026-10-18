// KAOS 1.6.53: observation-only multi-horizon market-outcome collector.
// Uses the first observed tick AT OR AFTER expiry, within 2 seconds. Missing
// observations and equal prices are excluded; no fabricated wins or broker fills.
(function(root){
  'use strict';
  const H=[5000,10000,15000,20000,25000,30000,60000];
  const pending=new Map(), done=[]; const MAX_PENDING=400,MAX_DONE=4000;
  function validX(x){return Array.isArray(x)&&x.length===104&&x.every(v=>typeof v==='number'&&Number.isFinite(v));}
  function classify(raw){
    const v=String(raw||'').toUpperCase();
    if(/REVERS|SWEEP|REJECTION|SR_FAILURE/.test(v))return 'REVERSAL';
    if(/BREAKOUT|SQUEEZE|DONCHIAN/.test(v))return 'BREAKOUT';
    if(/RUNNER|CONTINU|TREND_RESUME|TREND_PULLBACK|PULLBACK/.test(v))return 'RUNNER';
    return null; // Unknown setups cannot be assigned a specialist retroactively.
  }
  function snapshot(asset,price,x,t,marketClass){
    const specialist=classify(marketClass);
    if(!asset||!Number.isFinite(price)||price<=0||!validX(x)||!Number.isFinite(t))return false;
    const key=String(asset)+':'+Math.floor(t/5000);
    if(pending.has(key))return false;
    pending.set(key,{asset:String(asset),price,x:x.slice(),t,settled:[],key,specialist});
    while(pending.size>MAX_PENDING)pending.delete(pending.keys().next().value);
    return true;
  }
  function tick(asset,price,t){
    if(!asset||!Number.isFinite(price)||price<=0||!Number.isFinite(t))return 0;
    let count=0;
    for(const [key,s] of pending){
      if(s.asset!==String(asset))continue;
      for(const h of H){
        if(s.settled.includes(h))continue;
        const due=s.t+h;
        if(t<due)continue;
        s.settled.push(h);
        if(t-due<=2000 && price!==s.price){
          done.push({asset:s.asset,t:s.t,x:s.x.slice(),label:price>s.price?1:0,targetHorizonMs:h,entryPrice:s.price,exitPrice:price,settlementTs:t,source:'observed_tick_shadow',specialist:s.specialist});
          count++;
        }
      }
      if(s.settled.length===H.length||t>s.t+62000)pending.delete(key);
    }
    if(done.length>MAX_DONE)done.splice(0,done.length-MAX_DONE);
    return count;
  }
  function drain(){return done.splice(0,done.length);}
  function stats(){return {pending:pending.size,completed:done.length,expiries:H.slice()};}
  root.KaosExpiryCollector={snapshot,tick,drain,stats};
})(typeof globalThis!=='undefined'?globalThis:this);
