import React from "react";
export default function ReplayTradeChart({candles=[],trades=[]}) {
 const bars=candles.slice(-250);
 if (!bars.length) return <p>No historical candles.</p>;
 const w=900,h=260,hi=Math.max(...bars.map(c=>c.high)),lo=Math.min(...bars.map(c=>c.low));
 const y=v=>20+(hi-v)/Math.max(hi-lo,0.000000001)*220;
 const x=t=>20+(t-bars[0].ts)/Math.max(bars[bars.length-1].ts-bars[0].ts,1)*860;
 return <svg viewBox="0 0 900 260" role="img" aria-label="Historical candle chart with trade markers" className="w-full rounded bg-black">
 {bars.map(c=><g key={c.ts}><line x1={x(c.ts)} x2={x(c.ts)} y1={y(c.high)} y2={y(c.low)} stroke={c.close>=c.open?"#22c55e":"#ef4444"}/><rect x={x(c.ts)-1.5} width="3" y={Math.min(y(c.open),y(c.close))} height={Math.max(1,Math.abs(y(c.open)-y(c.close)))} fill={c.close>=c.open?"#22c55e":"#ef4444"}/></g>)}
 {trades.filter(t=>t.entry_ts>=bars[0].ts&&t.entry_ts<=bars[bars.length-1].ts).map((t,i)=><g key={i}><circle cx={x(t.entry_ts)} cy={y(t.entry_price)} r="5" fill={t.direction==="CALL"?"#60a5fa":"#f59e0b"}/><circle cx={x(t.exit_ts)} cy={y(t.exit_price)} r="3" fill={t.outcome==="WIN"?"#22c55e":"#ef4444"}/></g>)}
 </svg>;
}
