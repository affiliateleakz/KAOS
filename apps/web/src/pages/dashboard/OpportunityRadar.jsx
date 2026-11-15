import React,{useEffect,useRef,useState} from "react";
import {Link} from "react-router-dom";
import {api,errMsg} from "../../lib/api";
import {useAuth} from "../../context/AuthContext";
const classes=["all","stock","etf","option","crypto","dex","forex","future"];
const categories=[["all","All evidence"],["social","Social mentions"],["news","News"],["technical","Market"],["insider","Insiders"],["onchain","Whales"],["politician","Government"],["filing","Filings"],["institutional","Institutions"],["options_flow","Options"]];
const labels={reddit:'Reddit',x:'X',bluesky:'Bluesky',facebook:'Facebook Page',news:'News',market:'Market',sec:'SEC Form 4',ethereum:'ETH large transfers',government:'Congress disclosures'};
const positive=new Set(['collected','complete','no_matches']);
const when=value=>value?new Date(value).toLocaleString():'Not supplied';
function parseWatchlist(value){
 const assets=value.split(',').map(part=>part.trim()).filter(Boolean).map(part=>{const [symbol,kind='stock',extra]=part.split(':');if(extra||!symbol||!classes.includes(kind.toLowerCase())||kind.toLowerCase()==='all'||!/^[A-Za-z][A-Za-z0-9.]{0,11}$/.test(symbol))throw Error('Use SYMBOL:class, e.g. AAPL:stock, BTC:crypto.');return {symbol:symbol.toUpperCase(),asset_class:kind.toLowerCase()};});
 if(!assets.length||assets.length>5||new Set(assets.map(a=>a.symbol)).size!==assets.length)throw Error('Choose one to five different symbols per scan.');return assets;
}
export default function OpportunityRadar(){
 const {user}=useAuth();
 const [asset,setAsset]=useState('all'),[category,setCategory]=useState('all'),[provider,setProvider]=useState('all');
 const [saved,setSaved]=useState(null),[scan,setScan]=useState(null),[readiness,setReadiness]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false);
 const [statusError,setStatusError]=useState('');
 const [watchlist,setWatchlist]=useState('AAPL:stock, NVDA:stock, BTC:crypto, ETH:crypto'),[includeAI,setIncludeAI]=useState(true),[automatic,setAutomatic]=useState(false);
 const activeScan=useRef(false),scanRef=useRef(null);
 const load=async()=>{setLoading(true);try{const params=new URLSearchParams({limit:'50'});if(asset!=='all')params.set('asset_class',asset);if(category!=='all')params.set('source_filter',category);const r=await api.get('/api/v1/intelligence/opportunities?'+params);setSaved(r.data);}catch(e){setError(errMsg(e));}finally{setLoading(false);}};
 useEffect(()=>{load();},[asset,category]);
 useEffect(()=>{let alive=true;api.get('/api/v1/intelligence/scan/status').then(r=>{if(alive)setReadiness(r.data);}).catch(()=>{if(alive)setStatusError('Source configuration status is unavailable. Check that the updated Radar backend is installed.');});api.get('/api/v1/intelligence/scan/latest').then(r=>{if(alive)setScan(r.data.scan);}).catch(()=>{});return()=>{alive=false;};},[]);
 const run=async()=>{
  if(activeScan.current)return;let assets;try{assets=parseWatchlist(watchlist);}catch(e){setError(e.message);return;}
  activeScan.current=true;setBusy(true);setError('');
  try{const r=await api.post('/api/v1/intelligence/scan',{assets,include_ai:includeAI},{timeout:55000});setScan(r.data);await load();}
  catch(e){setError(errMsg(e)||'Scan could not finish. Source failures are not zero mention counts.');}
  finally{activeScan.current=false;setBusy(false);}
 };
 scanRef.current=run;
 useEffect(()=>{if(!automatic)return;const timer=setInterval(()=>{if(!document.hidden)scanRef.current?.();},300000);return()=>clearInterval(timer);},[automatic]);
 const evidence=(scan?.evidence||[]).filter(row=>(asset==='all'||row.asset_class===asset)&&(category==='all'||row.source===category)&&(provider==='all'||row.provider===provider));
 const statuses=scan?.source_status||[];
 const reports=scan?.ai?.report?.assets||[];
 const aiReady=readiness?.providers?.find(p=>p.id==='openai');
 return <section className="kaos-radar-screen space-y-5" data-testid="kaos-opportunity-radar">
  <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="label-mono text-xs tracking-widest">KAOS RESEARCH INTELLIGENCE</p><h1 className="mt-2 text-3xl font-bold text-[#D4AF37]">Opportunity Radar</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">News, Reddit & X, social samples, whale transfers, insider and government disclosures—one evidence workspace. AI reviews what was actually collected; it does not place orders.</p></div>{user?.role==='super_admin'&&<Link to="/admin/radar" className="rounded border border-[#8b6b32] px-4 py-2 text-sm text-[#e8c46f]">Configure sources & AI</Link>}</header>
  <section className="card-surface space-y-4 p-5" aria-label="Research scan controls">
   <label className="block text-sm text-slate-300" htmlFor="radar-watchlist">Watchlist · up to 5 symbols</label>
   <input id="radar-watchlist" disabled={busy} value={watchlist} onChange={e=>setWatchlist(e.target.value)} maxLength={180} className="w-full rounded border border-[#61502e] bg-[#0b0d0b] p-3 text-sm"/>
   <p className="text-xs text-slate-400">Format: AAPL:stock, BTC:crypto. Also accepts etf, option, dex, forex and future; unconnected asset classes use stored collector evidence.</p>
   <div className="flex flex-wrap items-center gap-4">
    <button type="button" onClick={run} disabled={busy} className="min-h-11 rounded border border-[#efcf76] bg-[#d4af37] px-5 py-2 font-semibold text-black disabled:opacity-50">{busy?'Scanning connected sources…':includeAI?'Scan sources + AI':'Scan sources'}</button>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={busy} checked={includeAI} onChange={e=>setIncludeAI(e.target.checked)}/>Include AI analysis</label>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={automatic} onChange={e=>{setAutomatic(e.target.checked);if(e.target.checked)run();}}/>Auto scan every 5 minutes</label>
    <button type="button" onClick={load} className="rounded border border-slate-700 px-3 py-2 text-xs">Refresh saved evidence</button>
   </div>
   <p className="text-xs text-slate-400">Auto scan runs while this page is visible. Repeated identical scans reuse a five-minute report; new watchlists have a one-minute cooldown. {aiReady?.configured?'AI API is configured; successful analysis depends on provider access.':'AI needs a configured server API key; source collection can run without it.'}</p>
  </section>
  {statusError&&<p role="status" className="text-sm text-amber-200">{statusError}</p>}
  {error&&<div role="alert" className="rounded border border-amber-700 p-4 text-sm text-amber-200">{error}</div>}
  {scan&&<p className="text-xs text-slate-400">Last scan: {when(scan.completed_at)} · Watchlist: {(scan.assets||[]).map(a=>a.symbol).join(', ')} · {scan.cached?'Cached report':'Completed scan'} · {scan.coverage}</p>}
  <section aria-labelledby="radar-source-title"><h2 id="radar-source-title" className="mb-3 font-heading text-lg text-[#e8c46f]">Source collection & coverage</h2>
   <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(labels).map(([id,label])=>{
    const rows=statuses.filter(row=>row.provider===id),failures=rows.filter(row=>!positive.has(row.state)&&row.state!=='not_applicable');
    const config=readiness?.providers?.find(p=>p.id===id),observations=rows.reduce((n,r)=>n+(r.observations||0),0),successful=rows.some(r=>positive.has(r.state));
    return <article key={id} className="card-surface p-4" data-testid={'radar-source-'+id}><div className="flex justify-between gap-2"><h3 className="font-semibold">{label}</h3><span className={'text-xs '+(failures.length?'text-amber-300':successful?'text-emerald-300':'text-slate-400')}>{rows.length?(failures.length?(successful?'Partial coverage':'Needs attention'):'Checked'):(config?(config.enabled?(config.configured?'Ready to try':'Setup required'):'Disabled'):(['news','market'].includes(id)?'Public feed':'Status unavailable'))}</span></div>
     <p className="mt-2 text-xs leading-5 text-slate-400">{rows.length?`${observations} observations collected · ${rows.length} watchlist queries`:'No scan attempt in this report yet.'}</p>
     {failures.length>0&&<p className="mt-2 text-xs leading-5 text-amber-200">{failures[0].message} {failures[0].state==='setup_required'?'Configure this source in the admin panel.':''}</p>}
     {rows.some(r=>r.scope)&&<p className="mt-2 text-[11px] leading-5 text-slate-500">{rows.find(r=>r.scope)?.scope}</p>}
     <details className="mt-2 text-xs"><summary className="cursor-pointer text-[#cbb67c]">Per-symbol status</summary><ul className="mt-2 space-y-1">{rows.map((row,i)=><li key={i}>{row.asset}: {row.state.replaceAll('_',' ')}{row.inspected!=null?` · ${row.inspected} items inspected`:''}</li>)}</ul></details>
    </article>;
   })}</div>
  </section>
  <section className="card-surface p-5" aria-labelledby="radar-ai-title"><h2 id="radar-ai-title" className="font-heading text-xl text-[#e8c46f]">AI evidence review</h2>
   {!scan&&<p className="mt-2 text-sm text-slate-400">Run a scan to review connected sources together. Missing feeds will be listed as gaps.</p>}
   {scan?.ai?.state!=='complete'&&scan?.ai&&<p role="status" className="mt-3 text-sm text-amber-200">{scan.ai.message||scan.ai.state.replaceAll('_',' ')}</p>}
   {scan?.ai?.report&&<><p className="mt-3 text-sm leading-7">{scan.ai.report.summary}</p><p className="mt-2 text-xs text-slate-500">Model: {scan.ai.model} · {scan.ai.observations_reviewed??'—'} observations reviewed from a balanced sample · Research attention, not win probability or execution instructions</p><div className="mt-4 grid gap-3 md:grid-cols-2">{reports.map(row=><article key={row.symbol+row.asset_class} className="rounded border border-[#61502e] p-4"><h3 className="font-semibold text-[#e8c46f]">{row.symbol} · {row.priority} research priority</h3><p className="mt-2 text-sm leading-6 text-slate-300">{row.explanation}</p><ul className="mt-2 list-inside list-disc text-xs leading-6 text-slate-400">{row.limitations.map((text,i)=><li key={i}>{text}</li>)}</ul><div className="mt-2 flex flex-wrap gap-2">{row.evidence_ids.map(id=><a key={id} href={'#evidence-'+id} className="text-xs text-[#e8c46f] underline">Evidence {id.slice(0,6)}</a>)}</div></article>)}</div><ul className="mt-4 list-inside list-disc text-xs leading-6 text-amber-200">{scan.ai.report.coverage_gaps.map((gap,i)=><li key={i}>{gap}</li>)}</ul></>}
  </section>
  <nav className="flex flex-wrap gap-2" aria-label="Radar asset class">{classes.map(kind=><button key={kind} onClick={()=>setAsset(kind)} aria-pressed={asset===kind} className={'rounded border px-3 py-2 text-xs '+(asset===kind?'border-[#d4af37] text-[#e8c46f]':'border-slate-700 text-slate-400')}>{kind.toUpperCase()}</button>)}</nav>
  <nav className="flex flex-wrap gap-2" aria-label="Radar evidence type">{categories.map(([key,label])=><button key={key} onClick={()=>{setCategory(key);setProvider('all');}} aria-pressed={category===key} className={'rounded border px-3 py-2 text-xs '+(category===key?'border-[#d4af37] text-[#e8c46f]':'border-slate-700 text-slate-400')}>{label}</button>)}</nav>
  {category==='social'&&<div className="flex flex-wrap gap-2" role="group" aria-label="Social network filter">{['all','reddit','x','bluesky','facebook'].map(id=><button key={id} onClick={()=>setProvider(id)} aria-pressed={provider===id} className="rounded border border-[#61502e] px-3 py-2 text-xs">{labels[id]||'All social sources'}</button>)}</div>}
  <section aria-labelledby="radar-evidence-title"><h2 id="radar-evidence-title" className="font-heading text-lg text-[#e8c46f]">Collected evidence</h2><p className="mt-2 text-xs text-slate-400">{evidence.length} matching observations from the last scan. Social samples are not complete mention counts. Transfers and disclosures do not establish future price direction.</p>
   <div className="mt-4 grid gap-3 md:grid-cols-2">{evidence.map(row=><article key={row.id} id={'evidence-'+row.id} className="card-surface scroll-mt-24 p-4"><h3 className="font-semibold">{row.asset} · {labels[row.provider]||row.provider||row.source}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{row.summary}</p><p className="mt-2 text-xs text-slate-500">Source/disclosure time: {when(row.published_at)} · Observed: {when(row.observed_at)}</p>{/^https:\/\//.test(row.source_url||'')&&<a href={row.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex min-h-10 items-center text-xs text-[#e8c46f] underline">Open source ↗</a>}</article>)}</div>
   {!evidence.length&&<p className="mt-3 rounded border border-slate-700 p-4 text-sm text-slate-400">No matching evidence in this scan. Review the source statuses above; an unavailable feed is not evidence of no activity.</p>}
  </section>
  <details className="rounded border border-slate-700 p-4"><summary className="cursor-pointer text-sm text-[#e8c46f]">Stored research ranking {loading?'· loading…':''}</summary><p className="mt-2 text-xs text-slate-400">Recent stored observations, including separate collectors. Scores rank research attention, not profitability.</p><div className="mt-3 grid gap-3 md:grid-cols-2">{(saved?.results||[]).map(row=><article key={row.asset+row.asset_class} className="rounded border border-slate-700 p-3"><h3>{row.asset} · score {row.score}</h3><p className="text-xs text-slate-400">{row.status} · {row.independent_sources} evidence categories</p>{(row.evidence||[]).slice(0,6).map((item,i)=><p key={i} className="mt-2 text-xs leading-5">{item.source}: {item.summary}</p>)}</article>)}</div></details>
 </section>;
}
