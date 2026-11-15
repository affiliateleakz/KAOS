import React,{useEffect,useRef,useState} from 'react';
import {api,errMsg} from '../../lib/api';
import TrendingStocks from './TrendingStocks';
import MarketSentiment from './MarketSentiment';
import RadarNews from './RadarNews';
import OpportunityScanner from './OpportunityScanner';
const tabs=[['news','News'],['trending','Trending'],['ai','AI Signal'],['sentiment','Sentiment'],['bot','Bot Entries']];
export default function OpportunityRadar(){
 const [tab,setTab]=useState('news'),[symbol,setSymbol]=useState('AAPL'),[kind,setKind]=useState('stock'),[focus,setFocus]=useState(null);
 const [data,setData]=useState(null),[bot,setBot]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [clock,setClock]=useState(Date.now());const running=useRef(false);
 useEffect(()=>{if(tab!=='bot')return;const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[tab]);
 const analyzeSentiment=async()=>{
  if(running.current)return;const clean=symbol.trim().toUpperCase();
  if(!/^[A-Z][A-Z0-9.]{0,11}$/.test(clean)){setError('Enter a ticker such as AAPL or BTC.');return;}
  running.current=true;setBusy(true);setError('');setData(null);
  try{const r=await api.post('/api/v1/intelligence/signals/market',{assets:[{symbol:clean,asset_class:kind}],include_ai:true},{timeout:55000});setData(r.data);}
  catch(e){setError(errMsg(e));}finally{running.current=false;setBusy(false);}
 };
 const refreshBot=async()=>{if(running.current)return;running.current=true;setBusy(true);setError('');try{const r=await api.get('/api/v1/intelligence/signals/bot');setBot(r.data);}catch(e){setError(errMsg(e));}finally{running.current=false;setBusy(false);}};
 const signals=(bot?.signals||[]).filter(row=>clock<new Date(row.expiresAt).getTime());
 return <div className="space-y-5"><h1 className="font-heading text-3xl text-[#e8c46f]">KAOS Radar</h1>
 <nav aria-label="Radar sections" className="flex gap-1 overflow-x-auto border-b border-[#61502e]">{tabs.map(([id,label])=><button key={id} aria-current={tab===id?'page':undefined} onClick={()=>{setTab(id);setError('');}} className={'shrink-0 border-b-2 px-4 py-3 text-sm '+(tab===id?'border-[#d4af37] text-[#e8c46f]':'border-transparent text-slate-400')}>{label}</button>)}</nav>
 {tab==='news'&&<RadarNews/>}
 {tab==='trending'&&<TrendingStocks onAnalyze={(ticker,asset_class)=>{setSymbol(ticker);setKind(asset_class);setFocus({symbol:ticker,asset_class});setTab('ai');}}/>}
 {tab==='ai'&&<OpportunityScanner initialFocus={focus} onClearFocus={()=>setFocus(null)}/>}
 {tab==='sentiment'&&<><div className="flex flex-wrap gap-3"><input aria-label="Sentiment ticker" value={symbol} onChange={e=>setSymbol(e.target.value)} className="min-w-0 rounded border border-[#61502e] bg-black/20 p-3"/><select aria-label="Sentiment market" value={kind} onChange={e=>setKind(e.target.value)} className="rounded border border-[#61502e] bg-[#0a0d0b] p-3"><option value="stock">Stock</option><option value="crypto">Crypto</option><option value="forex">Forex</option><option value="etf">ETF</option></select><button disabled={busy} onClick={analyzeSentiment} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Analyzing…':'Check sentiment'}</button></div>{error&&<p role="alert">{error}</p>}<MarketSentiment reports={data?.signals||[]} completedAt={data?.completed_at}/></>}
 {tab==='bot'&&<section className="space-y-4"><div className="flex flex-wrap items-center gap-3"><p className="text-sm text-slate-400">Recent entries from your connected extension. These expire in seconds.</p><button disabled={busy} onClick={refreshBot} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Refreshing…':'Refresh entries'}</button></div>{error&&<p role="alert">{error}</p>}{bot&&!signals.length&&<p role="status">No fresh bot entries.</p>}{signals.map(row=><article key={row.id} className="card-surface p-5"><h2 className="text-xl text-[#e8c46f]">{row.asset} · {row.direction}</h2><p className="mt-2 text-sm text-slate-400">{row.platform} · {row.expiration} · {row.signalTimestamp||row.createdAt}</p></article>)}</section>}
 </div>;
}
