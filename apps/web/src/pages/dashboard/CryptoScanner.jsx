import React,{useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";
import BubbleMap from "../../components/BubbleMap";

const money=n=>n==null?"—":new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:2}).format(n);
const percent=n=>n==null?"—":(n>=0?"+":"")+n.toFixed(2)+"%";
function shade(change){
 if(change==null)return "#292929";
 const opacity=Math.min(.8,.16+Math.abs(change)/40);
 return change>=0?`rgba(21,128,61,${opacity})`:`rgba(185,28,28,${opacity})`;
}
export default function CryptoScanner(){
 const [query,setQuery]=useState("SOL"),[chain,setChain]=useState(""),[pairs,setPairs]=useState([]);
 const [sort,setSort]=useState("volume_24h"),[error,setError]=useState(""),[loading,setLoading]=useState(false),[loaded,setLoaded]=useState(false);
 // Market-wide bubble map is keyless (CoinGecko, then Coinbase) and served from a short cache.
 const [market,setMarket]=useState(null),[marketError,setMarketError]=useState(""),[marketLoading,setMarketLoading]=useState(false);
 const [timeframe,setTimeframe]=useState("change_24h");
 const loadMarket=async()=>{
  setMarketLoading(true);setMarketError("");
  try{const r=await api.get("/api/v1/crypto/market?limit=60");setMarket(r.data)}
  catch(e){setMarketError(errMsg(e)||"Crypto market data unavailable")}
  finally{setMarketLoading(false)}
 };
 useEffect(()=>{loadMarket()},[]);
 const scan=async(e)=>{
  e?.preventDefault();setError("");setLoading(true);
  try{const params=new URLSearchParams({q:query});if(chain)params.set("chain",chain);
   const response=await api.get("/api/v1/crypto/pairs?"+params);
   setPairs(response.data.pairs||[]);setLoaded(true);
  }catch(e){setPairs([]);setError(errMsg(e)||"Market data unavailable");}
  finally{setLoading(false)}
 };
 // Run the default search on mount so the heat map is never blank on arrival.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 useEffect(()=>{scan()},[]);
 const ordered=[...pairs].sort((a,b)=>(b[sort]??-Infinity)-(a[sort]??-Infinity));
 return <div className="space-y-5" data-testid="kaos-crypto-scanner">
  <div><h1 className="font-heading text-2xl font-bold">KAOS Crypto Scanner & Heat Map</h1>
   <p className="text-sm text-slate-400">Market-wide bubbles sized by market cap and coloured by gain or loss, plus DEX pair search. No API key needed for either view.</p></div>
  <div className="rounded border border-amber-600/40 p-3 text-xs text-amber-200">Discovery only. A token can have fake volume, concentrated liquidity, malicious contracts or manipulated prices. Heat map colours reflect reported price change, not an AI buy or sell recommendation.</div>
  <section className="card-surface p-4" data-testid="crypto-bubble-heatmap">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div><h2 className="font-heading text-lg font-semibold">Crypto market bubbles</h2>
     <p className="text-xs text-slate-400">{market?`${market.count} coins · ${market.provider} · bubble size = ${market.weighting.replace("_"," ")}`:"Loading the market-wide bubble map…"}</p></div>
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Bubble timeframe">
     {[["change_1h","1h"],["change_24h","24h"],["change_7d","7d"]].map(([key,label])=>
      <button key={key} onClick={()=>setTimeframe(key)} aria-pressed={timeframe===key}
       className={`rounded border px-3 py-1.5 text-xs ${timeframe===key?"border-[#D4AF37] bg-[#D4AF37]/10 text-[#D4AF37]":"border-[#3a3a3a] text-slate-300"}`}>{label}</button>)}
     <button onClick={loadMarket} disabled={marketLoading} className="rounded border border-[#3a3a3a] px-3 py-1.5 text-xs text-slate-300 disabled:opacity-50">{marketLoading?"Refreshing…":"Refresh"}</button>
    </div>
   </div>
   {marketError&&<p role="alert" className="mt-2 text-sm text-red-400">{marketError}</p>}
   {market&&market.failures?.length?<p className="mt-2 text-xs text-amber-300">Primary feed unavailable ({market.failures.join(", ")}); using a secondary free feed.</p>:null}
   {market&&<div className="mt-3"><BubbleMap items={market.coins} valueKey={market.weighting==="market_cap"?"market_cap":"volume_24h"} changeKey={timeframe}
     label={market.weighting==="market_cap"?"Market cap":"24h volume"} emptyText="The market snapshot came back empty."/></div>}
   {market&&<p className="mt-2 text-[11px] text-slate-500">Free data, no key: CoinGecko public market endpoint, falling back to Coinbase Exchange public stats. Aggregated third-party prices can be delayed or wrong; verify on an exchange before acting.</p>}
  </section>
  <h2 className="pt-2 font-heading text-lg font-semibold">Token & DEX pair search</h2>
  <form onSubmit={scan} className="flex flex-wrap gap-2">
   <input value={query} onChange={e=>setQuery(e.target.value)} minLength={2} maxLength={55} placeholder="Token symbol / pair" className="min-w-48 flex-1 rounded border border-[#444] bg-[#111] p-2"/>
   <select value={chain} onChange={e=>setChain(e.target.value)} className="rounded border border-[#444] bg-[#111] p-2">
    {["","solana","ethereum","base","bsc","arbitrum","polygon"].map(x=><option key={x} value={x}>{x||"All chains"}</option>)}
   </select>
   <button disabled={loading} className="rounded bg-[#D4AF37] px-4 py-2 font-semibold text-black">{loading?"Loading…":"Scan crypto"}</button>
  </form>
  <div className="flex flex-wrap items-center gap-2 text-sm"><label htmlFor="crypto-sort">Rank by</label>
   <select id="crypto-sort" value={sort} onChange={e=>setSort(e.target.value)} className="rounded border border-[#444] bg-[#111] p-2">
    <option value="volume_24h">24h volume</option><option value="liquidity_usd">Liquidity</option><option value="change_24h">24h gain</option><option value="market_cap">Market cap</option>
   </select><span className="text-xs text-slate-400">{pairs.length} pairs shown · Source: DEX Screener</span></div>
  {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
  {loaded&&!pairs.length&&!error&&<p className="text-sm text-slate-400">No matching reported pools. Search a token or contract address.</p>}
  {!!pairs.length&&<><h2 className="font-semibold">24h pair heat map</h2>
   <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-5">
    {ordered.slice(0,30).map(p=><a key={p.chain+":"+p.pair_address} href={p.url||"#"} target="_blank" rel="noopener noreferrer"
      style={{background:shade(p.change_24h)}} className="min-h-24 rounded border border-white/10 p-3 text-white hover:ring-2 hover:ring-[#D4AF37]"
      title={p.name+" · "+p.chain+" · "+p.dex}>
      <div className="truncate font-bold">{p.symbol||"Unknown"}</div><div className="text-xs opacity-80">{p.chain}</div>
      <div className="mt-2 text-xl font-bold">{percent(p.change_24h)}</div>
      <div className="text-xs">Volume: ${money(p.volume_24h)}</div></a>)}
   </div>
   <div className="overflow-x-auto rounded border border-[#333]"><table className="w-full min-w-[870px] text-left text-xs">
    <thead><tr className="border-b border-[#333] text-slate-400">{["Token","Chain / DEX","Price","1h","24h","Liquidity","24h volume","24h buys / sells","Pair"].map(v=><th key={v} className="p-3">{v}</th>)}</tr></thead>
    <tbody>{ordered.map(p=><tr key={p.chain+":"+p.pair_address} className="border-b border-[#242424]">
      <td className="p-3"><strong>{p.symbol}</strong><div className="max-w-40 truncate text-slate-400">{p.name}</div></td><td className="p-3">{p.chain} / {p.dex}</td>
      <td className="p-3">{p.price_usd==null?"—":"$"+p.price_usd}</td>
      <td className="p-3">{percent(p.change_1h)}</td><td className="p-3">{percent(p.change_24h)}</td>
      <td className="p-3">${money(p.liquidity_usd)}</td><td className="p-3">${money(p.volume_24h)}</td>
      <td className="p-3">{p.buys_24h??"—"} / {p.sells_24h??"—"}</td>
      <td className="p-3">{p.url?<a className="text-[#D4AF37] underline" href={p.url} target="_blank" rel="noopener noreferrer">DEX Screener</a>:"—"}</td></tr>)}</tbody>
   </table></div></>}
  <p className="text-xs text-slate-500">DEX Screener data is attributed to its source. Access and commercial use are subject to the provider's terms. No live orders placed.</p>
 </div>;
}
