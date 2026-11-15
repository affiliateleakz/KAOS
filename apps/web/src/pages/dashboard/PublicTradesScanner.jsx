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
 const [syncing,setSyncing]=useState(false),[syncNote,setSyncNote]=useState("");
 const [cik,setCik]=useState(""),[changes,setChanges]=useState(null),[comparisonError,setComparisonError]=useState("");
 const [topic,setTopic]=useState("politics"),[headlines,setHeadlines]=useState(null),[headlineError,setHeadlineError]=useState(""),[headlineBusy,setHeadlineBusy]=useState(false);
 const loadHeadlines=async(nextTopic=topic)=>{
  setHeadlineBusy(true);setHeadlineError("");
  try{const r=await api.get(`/api/v1/disclosures/headlines?topic=${nextTopic}`);setHeadlines(r.data)}
  catch(e){setHeadlines(null);setHeadlineError(errMsg(e)||"Free headline feed unavailable")}
  finally{setHeadlineBusy(false)}
 };
 useEffect(()=>{loadHeadlines("politics")},[]);
 const viewChanges=async()=>{setComparisonError("");setChanges(null);try{const r=await api.get("/api/v1/disclosures/institutional-changes?cik="+encodeURIComponent(cik));setChanges(r.data)}catch(e){setComparisonError(errMsg(e)||"Cannot load institutional holdings comparison")}};
 const syncSec=async()=>{
  if(!ticker.trim()){setError("Type a ticker above first, e.g. AAPL");return}
  setSyncing(true);setError("");setSyncNote("");
  try{const r=await api.post("/api/v1/disclosures/sync-sec?ticker="+encodeURIComponent(ticker.trim().toUpperCase()));
   setSyncNote(`SEC EDGAR: examined ${r.data.filings_examined} filing(s), imported ${r.data.transactions_imported} insider transaction(s) for CIK ${r.data.issuer_cik}.`);
   await load();
  }catch(e){setError(errMsg(e)||"SEC sync failed")}
  finally{setSyncing(false)}
 };
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
   <button type="button" onClick={load} disabled={loading} className="rounded bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-50">{loading?"Loading…":"Search disclosures"}</button>
   <button type="button" onClick={syncSec} disabled={syncing} className="rounded border border-[#555] px-4 py-2 text-sm disabled:opacity-50" title="Pulls the latest SEC Form 4 insider filings for this ticker. Free SEC data, no API key.">{syncing?"Fetching from SEC…":"Load latest SEC filings"}</button>
  </div>
  {syncNote&&<p className="text-xs text-emerald-400">{syncNote}</p>}
  {source&&<p className="text-xs text-slate-400">{INFO[source]}</p>}
  <section className="rounded border border-[#333] p-3 space-y-2">
   <h2 className="font-semibold">Institutional 13F Position Changes</h2>
   <p className="text-xs text-slate-400">Enter the SEC institutional filer CIK. Compares two recorded public quarterly filings, not intraday trades.</p>
   <div className="flex flex-wrap items-center gap-2"><input aria-label="Institutional filer CIK" type="number" min="1" value={cik} onChange={e=>setCik(e.target.value)} className="rounded border border-[#444] bg-[#151515] p-2" placeholder="SEC CIK"/><button disabled={!cik} onClick={viewChanges} className="rounded bg-[#D4AF37] px-3 py-2 text-black">View reported changes</button></div>
   {comparisonError&&<p role="alert" className="text-red-400">{comparisonError}</p>}
   {changes&&!changes.comparison_available&&<p className="text-xs text-amber-300">No verified two-quarter comparison stored for this filer yet.</p>}
   {changes?.data&&<><p className="text-xs text-slate-400">Reported filing dates: {changes.data.previous_filing_date} → {changes.data.latest_filing_date}</p>
     <div className="max-h-72 overflow-auto"><table className="w-full text-left text-xs"><thead><tr><th>CUSIP / issuer</th><th>Position change</th><th>Net reported shares</th></tr></thead><tbody>{(changes.data.changes||[]).map(r=><tr key={r.cusip} className="border-t border-[#333]"><td className="p-2">{r.issuer} ({r.cusip})</td><td className="p-2">{r.change}</td><td className="p-2">{r.net_reported_change}</td></tr>)}</tbody></table></div>
     <a href={changes.data.latest_source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-[#D4AF37] underline">Latest official SEC filing</a>
   </>}
  </section>
  {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
  <section className="rounded border border-[#333] p-3 space-y-2" data-testid="free-political-headlines">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <h2 className="font-semibold">Free political & Wall Street headlines</h2>
    <span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300">No key · free public feed</span>
   </div>
   <p className="text-xs text-slate-400">Public news index, cached for five minutes. Headlines are research leads, not verified filings or trade signals.</p>
   <div className="flex flex-wrap gap-1" role="group" aria-label="Headline topic">
    {[["politics","Congress & politics"],["wallstreet","Wall Street & insiders"],["markets","Markets"]].map(([key,label])=>
     <button key={key} onClick={()=>{setTopic(key);loadHeadlines(key)}} aria-pressed={topic===key}
      className={`rounded border px-3 py-1.5 text-xs ${topic===key?"border-[#D4AF37] bg-[#D4AF37]/10 text-[#D4AF37]":"border-[#3a3a3a] text-slate-300"}`}>{label}</button>)}
    <button onClick={()=>loadHeadlines()} disabled={headlineBusy} className="rounded border border-[#3a3a3a] px-3 py-1.5 text-xs text-slate-300 disabled:opacity-50">{headlineBusy?"Loading…":"Refresh"}</button>
   </div>
   {headlineError&&<p role="alert" className="text-sm text-red-400">{headlineError}</p>}
   {headlines?.headlines?.length?<ul className="divide-y divide-[#222]">{headlines.headlines.map((h,i)=>
    <li key={h.url+i} className="py-2 text-sm"><a href={h.url} target="_blank" rel="noopener noreferrer" className="text-slate-200 hover:text-[#D4AF37] underline decoration-[#333]">{h.title}</a>
     <div className="text-[11px] text-slate-500">{h.publisher}{h.published_at?` · ${h.published_at}`:""} · via {headlines.provider}</div></li>)}</ul>:
    (headlines&&!headlines.headlines?.length&&!headlineError?<p className="text-xs text-slate-400">The feed returned no articles right now.</p>:null)}
  </section>
  {data&&<section className="rounded border border-[#333] p-3"><h2 className="mb-3 font-semibold">Disclosed activity · {data.count} records</h2>
    {!data.records?.length?<p className="py-8 text-center text-slate-400">No verified disclosures in the KAOS database for this filter. Data collection must be configured; this does not imply nobody traded.</p>:<div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs">
     <thead><tr className="border-b border-[#333] text-slate-400">{["Filer","Source","Asset","Type","Transaction date","Filed","Disclosed range","Official filing"].map(h=><th key={h} className="p-2">{h}</th>)}</tr></thead>
     <tbody>{data.records.map((r,i)=><tr key={r.filing_id+"-"+i} className="border-b border-[#222]">
      <td className="p-2 font-medium">{r.filer}</td><td className="p-2">{r.source}</td>
      <td className="p-2">{r.ticker||r.asset}</td><td className="p-2">{r.action}</td>
      <td className="p-2">{r.transaction_date||"Not reported"}</td><td className="p-2">{r.filing_date}</td>
      <td className="p-2">{r.amount_min_usd==null?"Not specified":"$"+r.amount_min_usd.toLocaleString()+(r.amount_max_usd==null?"":" – $"+r.amount_max_usd.toLocaleString())}</td>
      <td className="p-2"><a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-[#D4AF37] underline">View official filing</a></td>
     </tr>)}</tbody>
    </table></div>}
   </section>}
 </main>;
}
