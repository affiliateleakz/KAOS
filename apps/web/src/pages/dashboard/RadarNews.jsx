import React,{useEffect,useState} from 'react';
import {api,errMsg} from '../../lib/api';
export default function RadarNews(){
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[search,setSearch]=useState('');
 const load=async()=>{setBusy(true);setError('');try{const r=await api.post('/api/v1/intelligence/news/feed',{}, {timeout:25000});setData(r.data);}catch(e){setError(errMsg(e));}finally{setBusy(false);}};
 useEffect(()=>{load();},[]);
 const articles=(data?.articles||[]).filter(r=>[r.title,r.summary,...(r.tickers||[])].join(' ').toLowerCase().includes(search.toLowerCase()));
 return <section className="space-y-4" aria-label="Market news"><div className="flex flex-wrap gap-3"><input aria-label="Find news" placeholder="Search news or ticker" value={search} onChange={e=>setSearch(e.target.value)} className="min-w-0 flex-1 rounded border border-[#61502e] bg-black/20 p-3"/><button onClick={load} disabled={busy} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Loading…':'Refresh news'}</button></div>
 {error&&<p role="alert">{error}</p>}{data?.message&&<p role="status" className="text-sm text-amber-200">{data.message}</p>}
 {!busy&&data&&!articles.length&&<p className="text-sm text-slate-400">No matching headlines available.</p>}
 <div className="grid gap-4 md:grid-cols-2">{articles.map((row,i)=><article key={row.source_url+i} className="card-surface p-5"><p className="text-xs text-slate-400">{row.source} · {new Date(row.published_at).toLocaleString()}</p><h2 className="mt-2 text-lg text-[#e8c46f]"><a href={row.source_url} target="_blank" rel="noopener noreferrer">{row.title}</a></h2>{row.summary&&<p className="mt-2 text-sm leading-6 text-slate-300">{row.summary}</p>}</article>)}</div></section>;
}
