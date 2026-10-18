import React,{useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";

const SOURCE=[["","All disclosures"],["house","House of Representatives"],["senate","U.S. Senate"],["sec_insider","SEC insider Forms 3/4/5"],["institutional_13f","Institutional 13F holdings"]];
const INFO={
 house:"Congressional trade reporting can lag the actual transaction.",
 senate:"Senate transaction filings can appear weeks after the trade.",
 sec_insider:"Insider filing data is historical and may include grants or exercises.",
 institutional_13f:"Quarterly institutional holdings snapshots are not exact trade executions."
};
export default function PublicTradesScanner(){
 const [source,setSource]=useState(""),[ticker,setTicker]=useState(""),[data,setData]=useState(null);
 const [error,setError]=useState(""),[loading,setLoading]=useState(false);
 const load=async()=>{
  setLoading(true);setError("");
  try{const params=new URLSearchParams({limit:"100"});if(source)params.set("source",source);if(ticker.trim())params.set("ticker",ticker.trim().toUpperCase());
   const r=await api.get("/api/v1/disclosures/trades?"+params.toString());setData(r.data);
  }catch(e){setData(null);setError(errMsg(e)||"Unable to load filings");}
  finally{setLoading(false)}
 };
 useEffect(()=>{load()},[source]);
 return <main className="space-y-5 p-2" data-testid="political-wallstreet-scanner">
  <header><h1 className="font-heading text-2xl font-bold">KAOS Political & Wall Street Trades Scanner</h1>
  <p className="text-sm text-slate-400">Publicly filed congressional transactions, company-insider disclosures and institutional holdings. Separate from the social-media scanner.</p></header>
  <div className="rounded border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-200">
   Disclosures are delayed. Filing date and transaction date are different. 13F reports holdings, not the exact time an institution bought or sold. These records are research data, not live copy-trading signals.
  </div>
  <div className="flex flex-wrap items-end gap-3">
   <label className="text-sm">Disclosure category<select value={source} onChange={e=>setSource(e.target.value)} className="mt-1 block rounded border border-[#444] bg-[#151515] p-2">{SOURCE.map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label>
   <label className="text-sm">Ticker<input value={ticker} onChange={e=>setTicker(e.target.value.toUpperCase().slice(0,24))} placeholder="e.g. AAPL" className="mt-1 block rounded border border-[#444] bg-[#151515] p-2" /></label>
   <button type="button" onClick={load} disabled={loading} className="rounded bg-[#2F8CFF] px-4 py-2 font-semibold text-black disabled:opacity-50">{loading?"Loading…":"Search disclosures"}</button>
  </div>
  {source&&<p className="text-xs text-slate-400">{INFO[source]}</p>}
  {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
  {data&&<section className="rounded border border-[#333] p-3"><h2 className="mb-3 font-semibold">Disclosed activity · {data.count} records</h2>
    {!data.records?.length?<p className="py-8 text-center text-slate-400">No verified disclosures in the KAOS database for this filter. Data collection must be configured; this does not imply nobody traded.</p>:<div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs">
     <thead><tr className="border-b border-[#333] text-slate-400">{["Filer","Source","Asset","Type","Transaction date","Filed","Disclosed range","Official filing"].map(h=><th key={h} className="p-2">{h}</th>)}</tr></thead>
     <tbody>{data.records.map((r,i)=><tr key={r.filing_id+"-"+i} className="border-b border-[#222]">
      <td className="p-2 font-medium">{r.filer}</td><td className="p-2">{r.source}</td>
      <td className="p-2">{r.ticker||r.asset}</td><td className="p-2">{r.action}</td>
      <td className="p-2">{r.transaction_date||"Not reported"}</td><td className="p-2">{r.filing_date}</td>
      <td className="p-2">{r.amount_min_usd==null?"Not specified":"$"+r.amount_min_usd.toLocaleString()+(r.amount_max_usd==null?"":" – $"+r.amount_max_usd.toLocaleString())}</td>
      <td className="p-2"><a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-[#2F8CFF] underline">View official filing</a></td>
     </tr>)}</tbody>
    </table></div>}
   </section>}
 </main>;
}
