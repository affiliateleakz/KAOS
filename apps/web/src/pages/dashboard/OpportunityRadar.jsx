import Offerings from './Offerings';
import React,{useEffect,useRef,useState} from 'react';
import {api,errMsg} from '../../lib/api';
import TrendingStocks from './TrendingStocks';
import RadarNews from './RadarNews';
import OpportunityScanner from './OpportunityScanner';
const tabs=[['news','News'],['research','Research'],['ai','AI Signal'],['bot','Bot Entries'],['offerings','IPOs & ICOs']];
export default function OpportunityRadar(){
 const [tab,setTab]=useState('news'),[selection,setSelection]=useState(null);
 const [researchOrigin,setResearchOrigin]=useState('trending'),[scannerPreferences,setScannerPreferences]=useState({market:'stocks',limit:5,timeframe:'daily'});
 const [bot,setBot]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [clock,setClock]=useState(Date.now());const running=useRef(false);
 useEffect(()=>{if(tab!=='bot')return;const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[tab]);
 const refreshBot=async()=>{if(running.current)return;running.current=true;setBusy(true);setError('');try{const r=await api.get('/api/v1/intelligence/signals/bot');setBot(r.data);}catch(e){setError(errMsg(e));}finally{running.current=false;setBusy(false);}};
 const signals=(bot?.signals||[]).filter(row=>clock<new Date(row.expiresAt).getTime());
 return <div className="space-y-5"><h1 className="font-heading text-3xl text-[#e8c46f]">KAOS Radar</h1>
 <nav aria-label="Radar sections" className="flex gap-1 overflow-x-auto border-b border-[#61502e]">{tabs.map(([id,label])=><button key={id} aria-current={tab===id?'page':undefined} onClick={()=>{setTab(id);setError('');if(id==='research'){setSelection(null);setResearchOrigin('trending');}}} className={'shrink-0 border-b-2 px-4 py-3 text-sm '+(tab===id?'border-[#d4af37] text-[#e8c46f]':'border-transparent text-slate-400')}>{label}</button>)}</nav>
 {tab==='news'&&<RadarNews/>}
 {tab==='offerings'&&<Offerings/>}
 {tab==='research'&&<TrendingStocks selection={selection} backLabel={researchOrigin==='ai'?'← Back to AI Signal':'← Back to trending'} onSelect={asset=>{setSelection(asset);if(!asset&&researchOrigin==='ai')setTab('ai');if(asset)setResearchOrigin('trending');}}/>}
 {tab==='ai'&&<OpportunityScanner initialTimeframe={scannerPreferences.timeframe} initialMarket={scannerPreferences.market} initialLimit={scannerPreferences.limit} onPreferences={setScannerPreferences} onResearch={asset=>{setSelection(asset);setResearchOrigin('ai');setTab('research');}}/>}
 {tab==='bot'&&<section className="space-y-4"><div className="flex flex-wrap items-center gap-3"><p className="text-sm text-slate-400">Recent entries from your connected extension. These expire in seconds.</p><button disabled={busy} onClick={refreshBot} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Refreshing…':'Refresh entries'}</button></div>{error&&<p role="alert">{error}</p>}{bot&&!signals.length&&<p role="status">No fresh bot entries.</p>}{signals.map(row=><article key={row.id} className="card-surface p-5"><h2 className="text-xl text-[#e8c46f]">{row.asset} · {row.direction}</h2><p className="mt-2 text-sm text-slate-400">{row.platform} · {row.expiration} · {row.signalTimestamp||row.createdAt}</p></article>)}</section>}
 </div>;
}
