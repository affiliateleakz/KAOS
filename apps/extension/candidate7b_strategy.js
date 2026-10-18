// KAOS S/R v1.1: closed-candle, structure-confirmed deterministic baseline.
// This is NOT a trained AI or a promise of profitability.
(()=>{'use strict';
const CFG=Object.freeze({name:'KAOS_STRATEGY',version:'SR1.1',srLookback:20,expiries:[15,20,25]});
function aggregate(rows,sec){const ms=sec*1000,out=[];let b=null;for(const r of rows){const ts=Number(r.ts),end=Number(r.closeTs);if(!Number.isFinite(ts)||!Number.isFinite(end)||end<=ts)continue;const k=Math.floor(ts/ms)*ms;if(!b||b.ts!==k){if(b)out.push(b);b={ts:k,open:+r.open,high:+r.high,low:+r.low,close:+r.close,closeTs:end};}else{b.high=Math.max(b.high,+r.high);b.low=Math.min(b.low,+r.low);b.close=+r.close;b.closeTs=Math.max(b.closeTs,end);}}if(b)out.push(b);return out.filter(r=>r.closeTs>=r.ts+ms-1);}
function ema(a,p){if(a.length<p)return NaN;let v=a.slice(0,p).reduce((s,x)=>s+x,0)/p,k=2/(p+1);for(let i=p;i<a.length;i++)v+=k*(a[i]-v);return v;}
function atr(q,p){if(q.length<p+1)return NaN;let z=0;for(let i=q.length-p;i<q.length;i++){const c=q[i],prev=q[i-1].close;z+=Math.max(c.high-c.low,Math.abs(c.high-prev),Math.abs(c.low-prev));}return z/p;}
function pack(engine,dir,expiry,reason,extra){const s={engine,dir,expiry,confidence:null,reason,...extra};return {...s,signals:[s]};}
function signal(rows){const q5=aggregate(rows,5),q15=aggregate(rows,15),q30=aggregate(rows,30),q60=aggregate(rows,60);if(q5.length<60||q30.length<25||q60.length<24)return null;
const c=q5.at(-1),p=q5.at(-2),p2=q5.at(-3),a30=atr(q30,14);if(!Number.isFinite(a30)||a30<=0)return null;
const hist=q30.slice(-21,-1);if(hist.length<20)return null;const support=Math.min(...hist.map(x=>x.low)),resistance=Math.max(...hist.map(x=>x.high));
const e9=ema(q60.map(x=>x.close),9),e21=ema(q60.map(x=>x.close),21),bullCtx=e9>e21&&q60.at(-1).close>q60.at(-3).close,bearCtx=e9<e21&&q60.at(-1).close<q60.at(-3).close;
const bull=c.close>c.open,bear=c.close<c.open,range=Math.max(1e-12,c.high-c.low),body=Math.abs(c.close-c.open)/range,lower=(Math.min(c.open,c.close)-c.low)/range,upper=(c.high-Math.max(c.open,c.close))/range,extra={support,resistance};
// Demand a closed 5s confirmation candle. Rejections must not be against the 60s trend.
if(bullCtx&&bull&&body>=.30&&lower>=.28&&Math.abs(c.low-support)<=.28*a30&&c.close>support+.10*a30)return pack('SR_REJECTION','BUY',20,'Support rejection confirmed in 60s uptrend',extra);
if(bearCtx&&bear&&body>=.30&&upper>=.28&&Math.abs(c.high-resistance)<=.28*a30&&c.close<resistance-.10*a30)return pack('SR_REJECTION','SELL',20,'Resistance rejection confirmed in 60s downtrend',extra);
// Sweep and reclaim; require both confirmation and aligned context.
if(bullCtx&&p.low<support-.12*a30&&p.close>=support&&bull&&c.close>p.high)return pack('FAILED_BREAK_RECLAIM','BUY',20,'Support sweep and reclaim confirmed',extra);
if(bearCtx&&p.high>resistance+.12*a30&&p.close<=resistance&&bear&&c.close<p.low)return pack('FAILED_BREAK_RECLAIM','SELL',20,'Resistance sweep and reclaim confirmed',extra);
if(bullCtx&&p2.close>resistance+.12*a30&&p.low<=resistance+.28*a30&&p.close>=resistance&&bull&&c.close>p.high)return pack('BREAKOUT_RETEST','BUY',25,'Breakout and retest confirmed',extra);
if(bearCtx&&p2.close<support-.12*a30&&p.high>=support-.28*a30&&p.close<=support&&bear&&c.close<p.low)return pack('BREAKOUT_RETEST','SELL',25,'Breakdown and retest confirmed',extra);
const q15c=q15.at(-1),q15p=q15.at(-2),priorEma=ema(q15.slice(0,-1).map(x=>x.close),9);
if(bullCtx&&bull&&q15p.close<q15p.open&&q15c.close>q15c.open&&q15c.close>q15p.high&&q15p.low<=priorEma&&c.close>q15p.high)return pack('TREND_PULLBACK','BUY',15,'15s bullish pullback continuation confirmed',extra);
if(bearCtx&&bear&&q15p.close>q15p.open&&q15c.close<q15c.open&&q15c.close<q15p.low&&q15p.high>=priorEma&&c.close<q15p.low)return pack('TREND_PULLBACK','SELL',15,'15s bearish pullback continuation confirmed',extra);
return null;}
function sleeve(rows,engines){const s=signal(rows);return s&&engines.includes(s.engine)?s:null;}
window.KAOSCandidate7B=Object.freeze({config:CFG,signal,reversal:rows=>sleeve(rows,['SR_REJECTION','FAILED_BREAK_RECLAIM']),runner:rows=>sleeve(rows,['TREND_PULLBACK']),breakout:rows=>sleeve(rows,['BREAKOUT_RETEST']),aggregate});})();
