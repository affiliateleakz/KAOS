import React,{useEffect,useRef,useState} from 'react';
import {api,errMsg} from '../../lib/api';
import StockMentions from './StockMentions';
import MarketSentiment from './MarketSentiment';
import RadarNews from './RadarNews';
const tabs=[['news','News'],['social','Social'],['ai','AI Signal'],['sentiment','Sentiment'],['bot','Bot Entries']];
export default function OpportunityRadar(){
 const [tab,setTab]=useState('news'),[symbol,setSymbol]=useState('AAPL'),[kind,setKind]=useState('stock');
 const [data,setData]=useState(null),[bot,setBot]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [clock,setClock]=useState(Date.now());const running=useRef(false);
 useEffect(()=>{if(tab!=='ai'&&tab!=='bot')return;const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[tab]);
 const analyze=async(selectedSymbol=symbol,selectedKind=kind)=>{
  if(running.current)return;
  const clean=selectedSymbol.trim().toUpperCase();
  if(!/^[A-Z][A-Z0-9.]{0,11}$/.test(clean)){setError('Enter a ticker such as AAPL or BTC.');return;}
  running.current=true;setBusy(true);setError('');setData(null);
  try{const r=await api.post('/api/v1/intelligence/signals/market',{assets:[{symbol:clean,asset_class:selectedKind}],include_ai:true},{timeout:55000});setData(r.data);}
  catch(e){setError(errMsg(e));}finally{running.current=false;setBusy(false);}
 };
 const refreshBot=async()=>{if(running.current)return;running.current=true;setBusy(true);setError('');try{const r=await api.get('/api/v1/intelligence/signals/bot');setBot(r.data);}catch(e){setError(errMsg(e));}finally{running.current=false;setBusy(false);}};
 const signals=tab==='bot'?(bot?.signals||[]).filter(row=>clock<new Date(row.expiresAt).getTime()):(data?.signals||[]).map(row=>row.expires_at&&clock>=new Date(row.expires_at).getTime()?{...row,direction:'WAIT',reason:'Scan again for a current signal.'}:row);
 return <div className="space-y-5"><h1 className="font-heading text-3xl text-[#e8c46f]">KAOS Radar</h1>
 <nav aria-label="Radar sections" className="flex gap-1 overflow-x-auto border-b border-[#61502e]">{tabs.map(([id,label])=><button key={id} aria-current={tab===id?'page':undefined} onClick={()=>{setTab(id);setError('');}} className={'shrink-0 border-b-2 px-4 py-3 text-sm '+(tab===id?'border-[#d4af37] text-[#e8c46f]':'border-transparent text-slate-400')}>{label}</button>)}</nav>
 {tab==='news'&&<RadarNews/>}
 {tab==='social'&&<StockMentions onAnalyze={(ticker,asset_class)=>{setSymbol(ticker);setKind(asset_class);setTab('ai');analyze(ticker,asset_class);}}/>}
 {tab==='sentiment'&&<><div className="flex flex-wrap gap-3"><input aria-label="Sentiment ticker" value={symbol} onChange={e=>setSymbol(e.target.value)} className="min-w-0 rounded border border-[#61502e] bg-black/20 p-3"/><button disabled={busy} onClick={()=>analyze()} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Analyzing…':'Check sentiment'}</button></div>{error&&<p role="alert">{error}</p>}<MarketSentiment reports={data?.signals||[]} completedAt={data?.completed_at}/></>}
 {(tab==='ai'||tab==='bot')&&<section className="space-y-4"><div className="flex flex-wrap items-center gap-3">{tab==='ai'?<><input aria-label="Signal ticker" placeholder="Ticker, e.g. AAPL" value={symbol} onChange={e=>setSymbol(e.target.value)} className="min-w-0 rounded border border-[#61502e] bg-black/20 p-3"/><select aria-label="Signal market" value={kind} onChange={e=>setKind(e.target.value)} className="rounded border border-[#61502e] bg-[#0a0d0b] p-3"><option value="stock">Stock</option><option value="etf">ETF</option><option value="crypto">Crypto</option></select><button disabled={busy} onClick={()=>analyze()} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Analyzing…':'Analyze'}</button><span className="text-xs text-slate-400">45–60 minute outlook</span></>:<><p className="text-sm text-slate-400">Recent entries from your connected extension. These expire in seconds.</p><button disabled={busy} onClick={refreshBot} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Refreshing…':'Refresh entries'}</button></>}</div>
 {error&&<p role="alert">{error}</p>}
 {tab==='ai'&&!data&&!busy&&<p className="text-sm text-slate-400">Choose a ticker. KAOS combines available market data and news into BUY, SELL or WAIT.</p>}
 {tab==='bot'&&bot&&!signals.length&&<p role="status">No fresh bot entries.</p>}
 {signals.map((row,i)=><article key={row.id||row.symbol||i} className="card-surface p-5"><div className="flex items-center justify-between gap-3"><h2 className="text-xl text-[#e8c46f]">{row.symbol||row.asset}</h2><strong className={row.direction==='BUY'?'text-emerald-300':row.direction==='SELL'?'text-red-300':'text-amber-200'}>{row.direction}</strong></div><p className="mt-3 text-sm leading-6">{row.model_state==='collecting'?'KAOS is learning from collected evidence. A validated model is needed before it can issue a signal.':row.reason||`${row.platform} · ${row.expiration||'Broker entry'}`}</p>
 <details className="mt-4 text-sm"><summary className="cursor-pointer text-[#e8c46f]">Why this signal?</summary><div className="mt-3 space-y-2 text-xs leading-6 text-slate-400">{row.model_state&&<p>Model: {row.model_state}</p>}{row.market_source&&<p>{row.market_source} · Last closed price: {row.reference_price}</p>}{row.model_score_up!=null&&<p>Upward model score: {row.model_score_up.toFixed(3)}. This is not a calibrated win probability.</p>}{row.factors?.map((f,j)=><p key={j}>{f.feature.replaceAll('_',' ')}: {f.contribution}</p>)}{row.supporting_sources?.map((r,j)=><p key={'source-'+j}>{r.summary} {/^https:\/\//.test(r.source_url||'')&&<a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-[#e8c46f] underline">Read source ↗</a>}</p>)}{row.limitations?.map((text,j)=><p key={'limit-'+j}>{text}</p>)}{data?.coverage_gaps?.map((text,j)=><p key={'gap-'+j}>{text}</p>)}</div></details></article>)}
 </section>}
 </div>;
}
