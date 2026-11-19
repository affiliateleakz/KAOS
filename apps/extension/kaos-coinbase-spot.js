/* Coinbase-only one-minute trend/breakout candidate. No profitability claim. */
(function(root){
 'use strict';
 function candles(raw,now){
  if(!Array.isArray(raw))throw Error('Invalid Coinbase candles');
  const rows=raw.map(r=>({ts:Number(r[0])*1000,low:Number(r[1]),high:Number(r[2]),open:Number(r[3]),close:Number(r[4])})).filter(r=>r.ts+60000<=now).sort((a,b)=>a.ts-b.ts).slice(-100);
  if(rows.length<60)throw Error('Waiting for 60 closed one-minute candles');
  for(let i=0;i<rows.length;i++){
   const r=rows[i];if(![r.ts,r.low,r.high,r.open,r.close].every(Number.isFinite)||r.low<=0||r.low>Math.min(r.open,r.close)||r.high<Math.max(r.open,r.close)||r.ts%60000!==0)throw Error('Invalid candle price or time');
   if(i&&r.ts!==rows[i-1].ts+60000)throw Error('Candle gap; entries paused');
  }
  if(now-(rows.at(-1).ts+60000)>90000)throw Error('Closed candle feed is stale');
  return rows;
 }
 function ema(rows,period){let value=rows[0].close;for(const r of rows.slice(1))value+=(r.close-value)*2/(period+1);return value;}
 function signal(rows){
  const last=rows.at(-1),before=rows.slice(0,-1),fast=ema(rows,20),slow=ema(rows,50);
  const resistance=Math.max(...before.slice(-20).map(r=>r.high));
  return {stamp:last.ts,direction:fast>slow&&last.close>resistance?'BUY':last.close<fast?'SELL':'WAIT',reason:'1m EMA20/50 trend + 20-bar closed-candle breakout'};
 }
 function quote(raw,now){
  const bid=Number(raw.bid),ask=Number(raw.ask),stamp=Date.parse(raw.time);
  if(!Number.isFinite(bid)||!Number.isFinite(ask)||bid<=0||ask<bid||!Number.isFinite(stamp)||now-stamp< -2000||now-stamp>15000)throw Error('Coinbase quote is stale or invalid');
  return {bid,ask,stamp,spreadPct:(ask-bid)/ask*100};
 }
 const api={candles,signal,quote};root.KAOSCoinbaseSpot=api;
 if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
