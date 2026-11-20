import React from "react";

/** Shows actual archived candles and heuristic pattern spans, NOT screenshot detections. */
export default function HistoricalPatternChart({bars=[],patterns=[]}) {
  if (!Array.isArray(bars)||bars.length<2) return null;
  const width=800,height=280,pad=20;
  const values=bars.flatMap(b=>[Number(b.low),Number(b.high)]);
  if (!values.every(Number.isFinite)) return null;
  const lo=Math.min(...values),hi=Math.max(...values),range=Math.max(hi-lo,1e-9);
  const chartH=height-2*pad;
  const y=p=>pad+(hi-p)/range*chartH;
  const step=(width-2*pad)/bars.length;
  const x=i=>pad+(i+.5)*step;
  const seen=new Set();
  const visible=(patterns||[]).filter(p=>p.index>=0&&p.index<bars.length&&p.start_index>=0)
    .filter(p=>{const key=p.index+"-"+p.start_index;if(seen.has(key))return false;seen.add(key);return true;})
    .slice(-16);
  return <div className="rounded border border-[#333] bg-[#080808] p-2" data-testid="historic-candlestick-overlay">
    <p className="mb-2 text-xs text-slate-400">Archived candle chart with heuristic pattern highlights (not image-model boxes)</p>
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Historical candlestick chart with highlighted pattern regions"
      className="h-auto w-full">
      {visible.map((p,i)=>{
        const from=x(p.start_index)-step*.45,to=x(p.index)+step*.45;
        const border=p.direction==="bullish"?"#34d399":p.direction==="bearish"?"#f87171":"#d4af37";
        return <g key={i}>
          <rect x={from} y={pad} width={Math.max(1,to-from)} height={chartH}
            fill={border} fillOpacity=".08" stroke={border} strokeOpacity=".75" strokeWidth="1"/>
        </g>;
      })}
      {bars.map((b,i)=>{
        const up=b.close>=b.open;
        const color=up?"#22c55e":"#ef4444";
        const top=Math.min(y(b.open),y(b.close));
        const bodyHeight=Math.max(1.4,Math.abs(y(b.open)-y(b.close)));
        return <g key={b.ts??i}>
          <line x1={x(i)} x2={x(i)} y1={y(b.high)} y2={y(b.low)} stroke={color} strokeWidth="1.2"/>
          <rect x={x(i)-Math.max(1,step*.28)} y={top}
            width={Math.max(2,step*.56)} height={bodyHeight} fill={color}/>
        </g>;
      })}
    </svg>
    <p className="text-xs text-slate-500">{visible.length} highlighted formation regions across {bars.length} archived candles. Overlapping patterns may share a region.</p>
  </div>;
}
