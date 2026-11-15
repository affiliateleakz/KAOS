import React,{useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";
import BubbleMap from "../../components/BubbleMap";
const color=(n)=>n==null?"#303030":n>=0?`rgba(22,133,69,${Math.min(.87,.25+Math.abs(n)/12)})`:`rgba(184,40,45,${Math.min(.87,.25+Math.abs(n)/12)})`;
const fmt=n=>n==null?"—":(n>=0?"+":"")+n.toFixed(2)+"%";
export default function StockHeatmap(){
 const [data,setData]=useState(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const [sector,setSector]=useState("All"),[rank,setRank]=useState("change_pct");
 const [view,setView]=useState("bubbles");
 const reload=async()=>{setBusy(true);setError("");
  try{const r=await api.get("/api/v1/stocks/heatmap");setData(r.data)}
  catch(e){setData(null);setError(errMsg(e)||"Stock market data unavailable")}
  finally{setBusy(false)}
 };
 useEffect(()=>{reload()},[]);
 const groups=(data?.sectors||[]).filter(s=>sector==="All"||s.sector===sector);
 // Dollar volume makes bubble area reflect how much money actually changed hands.
 const bubbles=groups.flatMap(g=>g.stocks.map(s=>({...s,name:g.sector,dollar_volume:(s.price&&s.volume)?s.price*s.volume:null})));
 return <section className="space-y-5" data-testid="stock-market-heatmap">
  <div><h1 className="font-heading text-2xl font-bold">KAOS Stock Market Heat Map</h1>
   <p className="text-sm text-slate-400">US stock and ETF performance by sector, sourced from the configured market-data provider.</p></div>
  <div className="flex flex-wrap items-center gap-3">
   <label className="text-sm">Sector <select value={sector} onChange={e=>setSector(e.target.value)} className="ml-2 rounded border border-[#444] bg-[#111] p-2">
    <option>All</option>{(data?.sectors||[]).map(s=><option key={s.sector}>{s.sector}</option>)}</select></label>
   <label className="text-sm">Sort <select value={rank} onChange={e=>setRank(e.target.value)} className="ml-2 rounded border border-[#444] bg-[#111] p-2">
    <option value="change_pct">24h performance</option><option value="volume">Daily volume</option><option value="price">Price</option></select></label>
   <div className="flex items-center gap-1" role="group" aria-label="Heat map style">
    {[["bubbles","Bubbles"],["grid","Grid"]].map(([key,label])=>
     <button key={key} onClick={()=>setView(key)} aria-pressed={view===key}
      className={`rounded border px-3 py-2 text-sm ${view===key?"border-[#D4AF37] bg-[#D4AF37]/10 text-[#D4AF37]":"border-[#444] text-slate-300"}`}>{label}</button>)}
   </div>
   <button onClick={reload} disabled={busy} className="rounded bg-[#D4AF37] px-4 py-2 text-black">{busy?"Refreshing…":"Refresh stocks"}</button>
  </div>
  <p className="rounded border border-amber-600/30 p-3 text-xs text-amber-200">A curated watchlist, not every US-listed stock. The default IEX feed covers only part of US market trading, and quotes may be delayed. Heat map colors indicate reported price change, not trading recommendations.</p>
  {data?.disclaimer&&<p className="text-xs text-slate-500">{data.disclaimer}</p>}
  {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
  {data&&<><p className="text-xs text-slate-400">Provider: {data.provider} · Feed: {String(data.feed).toUpperCase()} · Research only{data.fallback?" · Free keyless source":""}</p>
   {view==="bubbles"?<div className="card-surface p-3">
    <h2 className="font-heading text-lg font-semibold">US stocks & ETFs by daily dollar volume</h2>
    <p className="mb-2 text-xs text-slate-400">{bubbles.length} quoted symbols · bubble size = price × reported volume · colour = reported % change</p>
    <BubbleMap items={bubbles} valueKey="dollar_volume" changeKey="change_pct" label="Daily $ volume" emptyText="No stock quotes came back for this view."/>
   </div>:groups.map(group=><div key={group.sector} className="space-y-2">
     <h2 className="font-semibold">{group.sector} <span className="text-xs font-normal text-slate-400">({group.stocks.length} quoted)</span></h2>
     {!group.stocks.length?<p className="text-xs text-slate-400">No available snapshot data for this sector.</p>:
     <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
      {[...group.stocks].sort((a,b)=>(b[rank]??-Infinity)-(a[rank]??-Infinity)).map(stock=><div key={stock.symbol} style={{background:color(stock.change_pct)}} className="min-h-24 rounded border border-white/10 p-3 text-white" title={stock.data_time||"Timestamp unavailable"}>
       <div className="font-bold">{stock.symbol}</div>
       <div className="mt-1 text-xl font-semibold">{fmt(stock.change_pct)}</div>
       <div className="mt-1 text-xs">{stock.price==null?"No quote":"$"+stock.price.toFixed(2)}</div>
       <div className="text-xs opacity-80">Vol: {stock.volume==null?"—":stock.volume.toLocaleString()}</div>
      </div>)}
     </div>}
   </div>)}
  </>}
 </section>;
}
