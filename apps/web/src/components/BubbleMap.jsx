import React,{useMemo,useState} from "react";

// Bubble heat map: each bubble's area is proportional to the weighted value
// (market cap, liquidity or volume) and its colour is the reported % change.
// Layout is deterministic: largest bubble first, placed on a spiral until it
// touches nothing. If the field does not fit, every radius shrinks and it retries,
// so the picture is stable between renders and never overlaps.

const WIDTH=1000,HEIGHT=620,GOLDEN=Math.PI*(3-Math.sqrt(5));

export const changeColor=change=>{
 if(change==null||!Number.isFinite(change))return "hsl(220,8%,32%)";
 const strength=Math.min(1,Math.abs(change)/8);
 const light=32+16*strength, sat=48+34*strength;
 return change>=0?`hsl(145,${sat}%,${light}%)`:`hsl(356,${sat}%,${light}%)`;
};

const money=n=>n==null?"—":new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:2}).format(n);
const percent=n=>n==null?"—":(n>=0?"+":"")+n.toFixed(2)+"%";

function layout(items){
 const usable=items.filter(i=>i.weight>0);
 if(!usable.length)return {circles:[],scale:1};
 const max=Math.max(...usable.map(i=>i.weight));
 let factor=(Math.min(WIDTH,HEIGHT)*0.30)/Math.sqrt(max);
 for(let attempt=0;attempt<14;attempt++){
  const circles=[];
  for(const item of usable){
   const r=Math.max(9,Math.sqrt(item.weight)*factor);
   let placed=null;
   for(let step=0;step<900;step++){
    const angle=step*GOLDEN;
    const radius=3.2*Math.sqrt(step)*(WIDTH/130);
    const x=WIDTH/2+Math.cos(angle)*radius;
    const y=HEIGHT/2+Math.sin(angle)*radius*0.62;
    if(x-r<4||x+r>WIDTH-4||y-r<4||y+r>HEIGHT-4)continue;
    if(circles.some(c=>Math.hypot(c.x-x,c.y-y)<c.r+r+2))continue;
    placed={x,y};break;
   }
   if(!placed)break;
   circles.push({...item,x:placed.x,y:placed.y,r});
  }
  if(circles.length===usable.length)return {circles,scale:factor};
  factor*=0.92;
 }
 return {circles:[],scale:factor};
}

export default function BubbleMap({items=[],valueKey="market_cap",changeKey="change_24h",label="Market cap",emptyText="No market data available.",onSelect}){
 const [hover,setHover]=useState(null);
 const prepared=useMemo(()=>{
  const rows=items
   .map(item=>({...item,weight:Number(item[valueKey])>0?Number(item[valueKey]):Number(item.volume_24h)>0?Number(item.volume_24h):0}))
   .sort((a,b)=>b.weight-a.weight)
   .slice(0,80);
  return layout(rows);
 },[items,valueKey]);
 const chosen=hover??null;
 if(!items.length)return <p className="rounded border border-[#333] bg-[#111] p-6 text-sm text-slate-400">{emptyText}</p>;
 return <div data-testid="bubble-map">
  <div className="overflow-hidden rounded-xl border border-[#262626] bg-[radial-gradient(circle_at_50%_40%,#171717_0%,#0c0c0c_70%)]">
   <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label+" bubble heat map"} className="block h-auto w-full">
    <defs>
     <radialGradient id="bubble-sheen" cx="35%" cy="30%" r="75%">
      <stop offset="0%" stopColor="#ffffff" stopOpacity="0.28"/>
      <stop offset="55%" stopColor="#ffffff" stopOpacity="0.06"/>
      <stop offset="100%" stopColor="#000000" stopOpacity="0.22"/>
     </radialGradient>
    </defs>
    {prepared.circles.map(c=>{
     const change=c[changeKey];
     const big=c.r>70, medium=c.r>42;
     return <g key={(c.symbol||"")+(c.pair_address||c.url||"")} className="cursor-pointer"
        onMouseEnter={()=>setHover(c)} onMouseLeave={()=>setHover(null)}
        onClick={()=>{if(onSelect)onSelect(c); else if(c.url)window.open(c.url,"_blank","noopener")}}>
      <title>{`${c.symbol||""} ${c.name?("· "+c.name):""} — ${percent(change)} (${label}: ${money(c[valueKey])})`}</title>
      <circle cx={c.x} cy={c.y} r={c.r} fill={changeColor(change)} stroke="#0a0a0a" strokeWidth="1.5"/>
      <circle cx={c.x} cy={c.y} r={c.r} fill="url(#bubble-sheen)" pointerEvents="none"/>
      {c.r>=13&&<text x={c.x} y={c.y-(medium?6:0)} textAnchor="middle" dominantBaseline="middle"
        fontSize={big?26:medium?16:Math.max(8,Math.min(12,c.r/1.6))} fontWeight="700" fill="#fff" pointerEvents="none">
        {String(c.symbol||"").slice(0,big?10:medium?7:4)}</text>}
      {medium&&<text x={c.x} y={c.y+16} textAnchor="middle" dominantBaseline="middle"
        fontSize={big?17:12} fontWeight="600" fill="#fff" fillOpacity="0.9" pointerEvents="none">{percent(change)}</text>}
      {big&&<text x={c.x} y={c.y+40} textAnchor="middle" dominantBaseline="middle"
        fontSize="12" fill="#fff" fillOpacity="0.75" pointerEvents="none">{label}: {money(c[valueKey])}</text>}
     </g>;
    })}
   </svg>
  </div>
  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
   <div className="flex flex-wrap items-center gap-2">
    {[[-8,"-8%+"],[-3,"-3%"],[-1,"-1%"],[0,"0%"],[1,"+1%"],[3,"+3%"],[8,"+8%+"]].map(([v,l])=>
      <span key={l} className="inline-flex items-center gap-1"><i className="inline-block h-3 w-3 rounded-full" style={{background:changeColor(v)}}/> {l}</span>)}
   </div>
   <span>Bubble size = {label.toLowerCase()} · Colour = % change · Click a bubble for its source.</span>
  </div>
  {chosen&&<div className="mt-2 rounded border border-[#333] bg-[#141414] p-3 text-xs" data-testid="bubble-detail">
   <strong className="text-[#D4AF37]">{chosen.symbol}</strong>{chosen.name&&chosen.name!==chosen.symbol?<span className="text-slate-400"> · {chosen.name}</span>:null}
   <span className="ml-3">Price ${chosen.price_usd??"—"}</span>
   <span className="ml-3">24h <span className={Number(chosen.change_24h)>=0?"text-emerald-400":"text-red-400"}>{percent(chosen.change_24h)}</span></span>
   {chosen.change_1h!=null&&<span className="ml-3">1h {percent(chosen.change_1h)}</span>}
   {chosen.change_7d!=null&&<span className="ml-3">7d {percent(chosen.change_7d)}</span>}
   <span className="ml-3 text-slate-400">{label}: {money(chosen[valueKey])}</span>
  </div>}
 </div>;
}
