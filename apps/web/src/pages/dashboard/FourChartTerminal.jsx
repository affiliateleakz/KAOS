import React, {useCallback,useEffect,useState} from "react";
import {api} from "../../lib/api";

// Four isolated chart configurations. This view does not place trades.
const DEFAULTS=[
 {broker:"kaos_paper",symbol:"BTC-USD",seconds:60},
 {broker:"kaos_paper",symbol:"ETH-USD",seconds:60},
 {broker:"kaos_paper",symbol:"SOL-USD",seconds:60},
 {broker:"kaos_paper",symbol:"BTC-USD",seconds:300},
];
function CandleChart({candles}){
 const bars=(candles||[]).slice(-70).map(c=>({o:Number(c.open),h:Number(c.high),l:Number(c.low),c:Number(c.close)}))
   .filter(c=>Object.values(c).every(Number.isFinite)&&c.h>=Math.max(c.o,c.c)&&c.l<=Math.min(c.o,c.c));
 if(!bars.length)return <div className="flex h-44 items-center justify-center text-xs text-slate-500">No validated candle data</div>;
 const high=Math.max(...bars.map(c=>c.h)),low=Math.min(...bars.map(c=>c.l)),range=Math.max(high-low,1e-10),w=700,h=190,bw=w/bars.length;
 const y=v=>8+(high-v)/range*(h-16);
 return <svg role="img" aria-label="Broker-sourced candle chart" viewBox={`0 0 ${w} ${h}`} className="h-44 w-full rounded bg-[#080808]" preserveAspectRatio="none">
  {bars.map((c,i)=>{const color=c.c>=c.o?"#22C55E":"#EF4444",x=i*bw+bw/2;return <g key={i}><line x1={x} x2={x} y1={y(c.h)} y2={y(c.l)} stroke={color} strokeWidth="1.3"/><rect x={i*bw+1} y={Math.min(y(c.o),y(c.c))} width={Math.max(1,bw-2)} height={Math.max(1,Math.abs(y(c.o)-y(c.c)))} fill={color}/></g>})}
 </svg>;
}
function Tile({index,config,onChange,onSave}){
 const [response,setResponse]=useState(null),[error,setError]=useState(""),[loading,setLoading]=useState(false);
 const load=useCallback(async()=>{
  if(config.broker!=="kaos_paper"){setResponse(null);setError("Broker chart integration not verified; no substitute prices shown.");return;}
  setLoading(true);
  try{
   const r=await api.get("/api/v1/paper/candles/"+encodeURIComponent(config.symbol)+"?granularity="+config.seconds);
   if(!Array.isArray(r.data?.candles))throw new Error("Invalid candle response");
   setResponse(r.data);setError("");
  }catch(e){setResponse(null);setError(e?.response?.data?.detail||"Candle feed unavailable");}
  finally{setLoading(false)}
 },[config.broker,config.symbol,config.seconds]);
 useEffect(()=>{load();const t=setInterval(()=>{if(!document.hidden)load()},15000);return()=>clearInterval(t)},[load]);
 return <article className="rounded-lg border border-slate-700 bg-[#101010] p-3" data-testid={`kaos-chart-${index+1}`}>
  <div className="mb-3 flex flex-wrap items-center gap-2">
   <strong className="text-sm">Chart {index+1}</strong>
   <select aria-label={`Chart ${index+1} broker`} value={config.broker} onChange={e=>onChange({...config,broker:e.target.value})} className="rounded bg-[#222] p-1 text-xs"><option value="kaos_paper">KAOS market data</option><option value="coinbase">Coinbase (pending chart verification)</option><option value="alpaca">Alpaca (pending live chart data)</option><option value="oanda">OANDA (pending live chart data)</option></select>
   <input aria-label={`Chart ${index+1} symbol`} value={config.symbol} onChange={e=>onChange({...config,symbol:e.target.value.toUpperCase().slice(0,32)})} className="w-28 rounded bg-[#222] p-1 text-xs"/>
   <select aria-label={`Chart ${index+1} timeframe`} value={config.seconds} onChange={e=>onChange({...config,seconds:Number(e.target.value)})} className="rounded bg-[#222] p-1 text-xs"><option value={60}>1m</option><option value={300}>5m</option><option value={900}>15m</option></select>
   <button type="button" onClick={load} className="ml-auto rounded border border-slate-600 px-2 py-1 text-xs">Refresh</button>
   <button type="button" onClick={()=>onSave(index,config)} className="rounded border border-[#2F8CFF] px-2 py-1 text-xs">Save chart</button>
  </div>
  {error?<p role="status" className="text-xs text-amber-300">{error}</p>:<CandleChart candles={response?.candles}/>}
  <p className="mt-2 text-xs text-slate-400">{loading?"Refreshing · ":""}Source: {response?.source||"Not available"} · read-only · no order submission</p>
 </article>;
}
export default function FourChartTerminal({entitlements}){
 const maxCharts=Math.max(1,Math.min(4,Number(entitlements?.chartLimit)||1));
 const [count,setCount]=useState(1),[configs,setConfigs]=useState(DEFAULTS);
 const [message,setMessage]=useState("");
 useEffect(()=>{
   let active=true;
   api.get("/api/v1/trading/charts").then(r=>{
     if(!active)return;
     const rows=r.data?.charts||[];
     setConfigs(old=>old.map((cfg,i)=>{const row=rows.find(x=>x.slot===i);return row?{broker:row.broker,symbol:row.symbol,seconds:row.seconds}:cfg}));
   }).catch(()=>{if(active)setMessage("Chart settings unavailable; selections may not be saved.")});
   return ()=>{active=false};
 },[]);
 const change=(i,v)=>setConfigs(old=>old.map((c,j)=>j===i?v:c));
 const save=(i,v)=>{
   api.put("/api/v1/trading/charts/"+i,v).then(()=>setMessage("Chart "+(i+1)+" settings saved.")).catch(()=>setMessage("Chart settings not saved; verify symbol, timeframe and membership."));
 };
 return <section className="mb-6 space-y-3" data-testid="kaos-four-chart-terminal">
  <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">KAOS Multi-Chart Terminal</h2><p className="text-xs text-slate-400">Independent chart settings (press Save chart to sync) · current source supports 1m, 5m and 15m Coinbase public candles only. Other feeds are unavailable. No real orders.</p></div>
   <label className="text-sm">Charts <select value={Math.min(count,maxCharts)} onChange={e=>setCount(Number(e.target.value))} className="ml-2 rounded bg-[#222] p-2">{Array.from({length:maxCharts},(_,i)=><option key={i} value={i+1}>{i+1}</option>)}</select></label>
  </div>
  {message && <p role="status" className="text-xs text-slate-400">{message}</p>}
  <div className="grid gap-3 lg:grid-cols-2">{configs.slice(0,Math.min(count,maxCharts)).map((cfg,i)=><Tile key={i} index={i} config={cfg} onChange={v=>change(i,v)} onSave={save}/>)}</div>
 </section>;
}
