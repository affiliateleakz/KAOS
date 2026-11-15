import React,{useEffect,useRef,useState} from 'react';
import {api,errMsg} from '../../lib/api';
const markets=[['stocks','Stocks'],['crypto','Crypto'],['forex','Forex'],['options','Options · calls/puts']];
export default function OpportunityScanner({initialFocus=null,onClearFocus}){
 const [market,setMarket]=useState(initialFocus?.asset_class==='crypto'?'crypto':initialFocus?.asset_class==='forex'?'forex':'stocks');
 const [limit,setLimit]=useState(5),[data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [clock,setClock]=useState(Date.now());const sequence=useRef(0),runRef=useRef(null),requestRef=useRef(null);
 const focus=initialFocus?.symbol||null;
 const run=async()=>{
  const id=++sequence.current;requestRef.current?.abort();const controller=new AbortController();requestRef.current=controller;
  setBusy(true);setError('');setData(null);
  try{const r=await api.post('/api/v1/intelligence/signals/opportunities',{market,limit,minimum_score:70,...(focus?{symbol:focus}:{})},{timeout:65000,signal:controller.signal});if(sequence.current===id)setData(r.data);}
  catch(e){if(sequence.current===id&&e.code!=='ERR_CANCELED')setError(errMsg(e));}
  finally{if(sequence.current===id)setBusy(false);}
 };
 runRef.current=run;
 useEffect(()=>{runRef.current();return()=>{sequence.current++;requestRef.current?.abort();};},[market,limit,focus]);
 useEffect(()=>{const id=setInterval(()=>{if(!document.hidden&&!busy)runRef.current?.();},market==='options'?60000:300000);return()=>clearInterval(id);},[busy,market]);
 useEffect(()=>{if(data?.state!=='collecting')return;const id=setTimeout(()=>runRef.current?.(),5000);return()=>clearTimeout(id);},[data]);
 useEffect(()=>{const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[]);
 const plays=(data?.plays||[]).filter(row=>clock<new Date(row.expires_at).getTime());
 return <section className="space-y-4" aria-label="AI opportunity scanner"><div className="flex flex-wrap items-end gap-3"><label className="text-sm">Trade<select aria-label="Opportunity market" value={market} onChange={e=>{onClearFocus?.();setMarket(e.target.value);}} className="mt-1 block rounded border border-[#61502e] bg-[#0a0d0b] p-3">{markets.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label><label className="text-sm">Show<select aria-label="Number of plays" value={limit} onChange={e=>setLimit(Number(e.target.value))} className="mt-1 block rounded border border-[#61502e] bg-[#0a0d0b] p-3">{Array.from({length:10},(_,i)=><option key={i+1} value={i+1}>{i+1} {i?'plays':'play'}</option>)}</select></label><button disabled={busy} onClick={run} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Scanning…':'Refresh plays'}</button></div>
 {focus&&<p className="text-sm text-slate-400">Focused on {focus}. <button onClick={onClearFocus} className="text-[#e8c46f] underline">Scan the market</button></p>}
 <p className="text-xs text-slate-400">Automatically scans a selected market watchlist. Shows up to {limit} setups scoring 70/100 or better. Score measures setup quality, not win probability.</p>
 {error&&<p role="alert" className="text-amber-200">{error}</p>}{data?.message&&<p role="status" className="text-sm text-slate-400">{data.message}</p>}
 {data?.plays?.length>0&&!plays.length&&<p role="status" className="text-sm text-slate-400">These plays have expired. Refresh for current setups.</p>}
 {data?.state==='complete'&&<p className="text-xs text-slate-400">{plays.length} qualifying plays · {data.scanned}/{data.universe_size} instruments checked{data.partial?' · Partial scan':''} · Updates every {market==='options'?'minute':'5 minutes'} while this tab is visible.</p>}
 <div className="grid gap-4 md:grid-cols-2">{plays.map((row,i)=><article key={row.option?.contract||row.symbol} className="card-surface p-5"><div className="flex items-center justify-between gap-3"><h2 className="text-xl text-[#e8c46f]">{i+1}. {row.display_symbol||row.symbol} · {row.direction}</h2><strong className="text-[#e8c46f]">{row.score}/100</strong></div><p className="mt-2 text-xs text-slate-400">{row.basis}</p><p className="mt-3 text-sm leading-6">{row.reason}</p>{row.option&&<div className="mt-3 text-sm"><p>{row.option.type} · Strike {row.option.strike} · Expires {row.option.expiry}</p><p className="mt-1">Bid {row.option.bid} / Ask {row.option.ask} · {row.option.source}</p><p className="mt-1 break-all text-xs text-slate-400">{row.option.contract}</p></div>}<p className="mt-3 text-xs text-slate-400">{row.option?'Underlying reference levels':'Reference levels'}: entry {row.reference_entry.toPrecision(6)} · stop {row.reference_stop.toPrecision(6)} · target {row.reference_target.toPrecision(6)}</p><p className="mt-2 text-xs text-slate-400">{row.horizon} outlook · Reference reward/risk {row.reward_risk}:1</p>
 <details className="mt-4 text-xs leading-6 text-slate-400"><summary className="cursor-pointer text-[#e8c46f]">Why this play?</summary><p>{row.source} · Closed candle: {row.source_time}</p><p>Model: {row.model_state}. {row.ai_confirmed?'Validated AI agrees.':'This is a technical setup; the AI has not confirmed it.'}</p>{Object.entries(row.score_components||{}).map(([key,value])=><p key={key}>{key.replaceAll('_',' ')}: {value}</p>)}{row.option_note&&<p>{row.option_note}</p>}{row.option&&<p>Option quote: {row.option.quote_time}</p>}{row.supporting_sources?.map((r,j)=><p key={j}>{r.summary} {/^https:\/\//.test(r.source_url||'')&&<a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-[#e8c46f] underline">Source ↗</a>}</p>)}</details></article>)}</div>
 {data&&<details className="text-xs leading-6 text-slate-400"><summary className="cursor-pointer text-[#e8c46f]">Scan details</summary><p>{data.universe_note}</p><p>{data.score_explanation}</p>{data.coverage?.map((text,i)=><p key={i}>{text}</p>)}<p>Options require fresh OPRA contracts. No qualified data means no play. Reference levels use closed prices and exclude trading costs.</p></details>}
 </section>;
}
