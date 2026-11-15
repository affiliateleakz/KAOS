import React,{lazy,Suspense,useEffect,useRef,useState} from 'react';
import {api,errMsg} from '../../lib/api';
import StockMentions from './StockMentions';
import MarketSentiment from './MarketSentiment';
const Evidence=lazy(()=>import('./RadarEvidence'));
export default function OpportunityRadar(){
 const [tab,setTab]=useState('market'),[data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[advanced,setAdvanced]=useState(false);
 const [automatic,setAutomatic]=useState(false);
 const running=useRef(false),activeRun=useRef(null);
 const [watchlist,setWatchlist]=useState('BTC:crypto, ETH:crypto, AAPL:stock, NVDA:stock');
 useEffect(()=>{setData(null);setError('');},[tab]);
 // Seconds-long entries expire locally, even when the member leaves this view open.
 const [clock,setClock]=useState(Date.now());
 useEffect(()=>{const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[]);
 const run=async(overrideAssets)=>{if(running.current)return;running.current=true;setBusy(true);setError('');setData(null);try{
  let response;
  if(tab==='bot')response=await api.get('/api/v1/intelligence/signals/bot');
  else{
   const assets=Array.isArray(overrideAssets)?overrideAssets:watchlist.split(',').map(x=>{const [symbol,asset_class='stock',extra]=x.trim().split(':');if(extra||!['crypto','stock','etf'].includes(asset_class)||!/^[A-Za-z][A-Za-z0-9.]{0,11}$/.test(symbol))throw Error('Use BTC:crypto or AAPL:stock; up to five symbols.');return {symbol,asset_class};});
   if(assets.length>5||!assets.length)throw Error('Choose one to five symbols.');
   response=await api.post('/api/v1/intelligence/signals/market',{assets,include_ai:true},{timeout:55000});
  }setData(response.data);
 }catch(e){setError(errMsg(e)||e.message);}finally{running.current=false;setBusy(false);}};
 activeRun.current=run;
 useEffect(()=>{if(!automatic||tab!=='market')return;const timer=setInterval(()=>{if(!document.hidden)activeRun.current?.();},300000);return()=>clearInterval(timer);},[automatic,tab]);
 const signals=(data?.signals||[]).filter(row=>tab!=='bot'||clock<new Date(row.expiresAt).getTime()).map(row=>tab==='market'&&row.expires_at&&clock>=new Date(row.expires_at).getTime()?{...row,direction:'WAIT',reason:'This scan has expired. Scan again for current evidence.'}:row);
 return <div className="space-y-5"><header><h1 className="font-heading text-3xl text-[#e8c46f]">KAOS Opportunity Radar</h1><p className="mt-2 text-slate-400">Find market setups. Keep broker entries separate from longer-term opportunities.</p></header>
 <nav aria-label="Signal horizon" className="flex flex-wrap gap-3">{[['market','Market opportunities · 45–60 minutes'],['social','Reddit & X · most mentioned'],['bot','Bot entries · seconds']].map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>{if(!busy)setTab(id);}} className="rounded border border-[#ad8c42] px-4 py-3 text-[#e8c46f]">{label}</button>)}</nav>
 {tab==='social'?<StockMentions onAnalyze={(symbol,asset_class)=>{setWatchlist(symbol+':'+asset_class);setTab('market');run([{symbol,asset_class}]);}}/>:<section className="card-surface space-y-4 p-5"><h2 className="text-xl text-[#e8c46f]">{tab==='market'?'Stock & crypto setups':'Connected broker signals'}</h2>
 <p className="text-sm text-slate-400">{tab==='market'?'Your KAOS model combines closed-candle price moves and volume with collected news, social activity and disclosures. It runs on the KAOS server without an external AI service. WAIT means no validated model or no clear signal. Optional data feeds may need owner credentials.':'Open your updated extension on the broker chart. Refresh here to see recent extension-reported entries. These are not independently verified or new order instructions; an entry may already be too late to follow.'}</p>
 {tab==='market'&&<label className="block text-sm">Watchlist<input className="mt-2 block w-full rounded border border-[#61502e] bg-black/30 p-3" value={watchlist} onChange={e=>setWatchlist(e.target.value)}/></label>}
 <button onClick={run} disabled={busy} className="rounded bg-[#d4af37] px-5 py-3 font-semibold text-black disabled:opacity-50">{busy?'Scanning…':tab==='market'?'Scan with KAOS AI':'Refresh bot entries'}</button>
 {tab==='market'&&<label className="ml-3 text-sm"><input type="checkbox" checked={automatic} onChange={e=>{setAutomatic(e.target.checked);if(e.target.checked)run();}}/> Monitor every 5 minutes while visible</label>}
 {error&&<p role="alert">{error}</p>}{data?.ai_status&&<p className="text-xs text-slate-400">{data.ai_status}</p>}
 {data&&signals.length===0&&<p role="status">No fresh bot entries. Start with the connected broker chart; no historical signal is treated as current.</p>}
 <div className="grid gap-4 md:grid-cols-2">{signals.map((row,i)=><article key={row.id||row.symbol||i} className="rounded border border-[#61502e] p-4"><h3 className="text-lg text-[#e8c46f]">{row.symbol||row.asset} · {row.direction}</h3><p className="mt-2 text-sm">{row.reason||`${row.platform} · ${row.engine||'Extension engine'} · ${row.expiration||'Expiry not supplied'}`}</p><p className="mt-2 text-xs text-slate-400">{row.source||data.provenance} · {row.source_time||row.signalTimestamp||row.createdAt}</p>{row.reference_stop!=null&&<p className="mt-2 text-sm">Reference stop: {row.reference_stop.toFixed(4)} · Target: {row.reference_target.toFixed(4)}</p>}<p className="mt-2 text-xs text-slate-500">{row.method||'Broker-specific entry; do not substitute spot or OTC symbols.'}</p>{row.market_source&&<p className="mt-2 text-xs text-slate-400">Market data: {row.market_source} · Last closed price: {row.reference_price}</p>}{row.model_state&&<p className="mt-2 text-xs text-amber-200">Model: {row.model_state} {row.model_version||''}</p>}{row.model_score_up!=null&&<p className="mt-2 text-xs text-slate-400">Upward model score: {row.model_score_up.toFixed(3)} · not a calibrated win probability</p>}{row.factors&&<p className="mt-2 text-xs text-slate-400">Model factors: {row.factors.map(f=>f.feature.replaceAll('_',' ')+' '+(f.contribution>=0?'+':'')+f.contribution).join(' · ')}. Contributions are model associations, not causes.</p>}{row.supporting_sources?.map((r,j)=><p key={'source-'+j} className="mt-2 text-xs text-[#e8c46f]">{r.source}: {r.summary} {/^(https:\/\/)/.test(r.source_url||'')&&<a href={r.source_url} target="_blank" rel="noopener noreferrer" className="underline">Read source ↗</a>}</p>)}{row.limitations?.map((text,j)=><p key={j} className="mt-2 text-xs text-slate-500">{text}</p>)}</article>)}</div>{data?.coverage_gaps?.map((text,i)=><p key={'gap-'+i} className="mt-2 text-xs text-amber-200">{text}</p>)}{data?.source_status&&<details className="text-xs text-slate-400"><summary>Data coverage and missing feeds</summary>{data.source_status.map((r,i)=><p key={i}>{r.asset} · {r.provider}: {r.state}</p>)}</details>}</section>}
 {tab==='market'&&<MarketSentiment reports={data?.signals||[]} completedAt={data?.completed_at}/>}
 <button aria-expanded={advanced} onClick={()=>setAdvanced(!advanced)} className="text-[#e8c46f] underline">{advanced?'Hide':'Open'} Advanced evidence & optional AI research</button>
 {advanced&&<Suspense fallback={<p>Loading evidence workspace…</p>}><Evidence/></Suspense>}
 </div>;
}
