import React,{useCallback,useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";
import {CandleChart} from "./FourChartTerminal";

const ROOT="/api/v1/owner/candles/r2-lab";
const selectClass="rounded border border-[#51472E] bg-[#101010] px-3 py-2 text-sm text-white";

export default function R2HistoryResearchPanel(){
  const [markets,setMarkets]=useState([]);
  const [market,setMarket]=useState("");
  const [limit,setLimit]=useState(200);
  const [history,setHistory]=useState(null);
  const [signals,setSignals]=useState([]);
  const [error,setError]=useState("");
  const [access,setAccess]=useState("");
  const [busy,setBusy]=useState(false);
  const loadMarkets=useCallback(async()=>{
    try{
      const {data}=await api.get(ROOT+"/markets");
      const list=Array.isArray(data.markets)?data.markets:[];
      setMarkets(list);setMarket(previous=>list.some(m=>m.symbol===previous)?previous:(list[0]?.symbol||""));
      setAccess("");
    }catch(e){
      setMarkets([]);setHistory(null);setSignals([]);
      setAccess(e?.response?.status===403?"R2 historical data and AI research are private to the KAOS owner.":errMsg(e)||"R2 market list unavailable");
    }
  },[]);
  useEffect(()=>{loadMarkets();},[loadMarkets]);
  const load=useCallback(async()=>{
    if(!market)return;
    setBusy(true);setError("");
    const [archive,forecast]=await Promise.allSettled([
      api.get(ROOT+"/history",{params:{symbol:market,limit}}),
      api.get(ROOT+"/bot-signal-preview",{params:{symbol:market,limit:8}})
    ]);
    if(archive.status==="fulfilled"){
      setHistory(archive.value.data);
    }else{
      setHistory(null);
      setError("R2 archive: "+(errMsg(archive.reason)||"unavailable"));
    }
    if(forecast.status==="fulfilled"){
      setSignals(forecast.value.data?.signals||[]);
    }else{
      setSignals([]);
      setError(previous=>(previous?previous+" · ":"")+"AI forecasts: "+(errMsg(forecast.reason)||"unavailable"));
    }
    setBusy(false);
  },[market,limit]);
  useEffect(()=>{load();},[load]);
  const latest=history?.candles?.[history.candles.length-1];
  const lastTs=history?.last_closed_ts;
  const isStale=lastTs?Date.now()-(Number(lastTs)+60000)>5*60000:true;
  return <section className="card-surface mb-6 space-y-3 p-5" data-testid="kaos-r2-history-terminal">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="font-heading text-lg font-semibold text-[#D4AF37]">KAOS AI · R2 Historical Intelligence</h2>
        <p className="mt-1 text-xs text-slate-400">Validated historical Cloudflare R2 candles + saved AI model forecasts · separate from current broker charts</p></div>
      <a href="/dashboard/backtests" className="text-xs text-[#D4AF37] underline">Open AI research &amp; backtesting</a>
    </div>
    {access?<p role="status" className="text-sm text-amber-300">{access}</p>:<>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-slate-300">R2 market
          <select className={"mt-1 block "+selectClass} value={market} onChange={e=>setMarket(e.target.value)}>
            {markets.map(m=><option key={m.symbol} value={m.symbol}>{m.symbol} · {m.asset_class}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-300">Historical candles
          <select className={"mt-1 block "+selectClass} value={limit} onChange={e=>setLimit(Number(e.target.value))}>
            <option value={200}>200</option><option value={500}>500</option><option value={1000}>1000</option>
          </select>
        </label>
        <button type="button" disabled={busy||!market} onClick={load} className="rounded bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">
          {busy?"Loading R2…":"Refresh R2 history"}
        </button>
      </div>
      {error&&<p role="alert" className="text-xs text-amber-300">{error}</p>}
      {history&&<div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded border border-[#37312A] p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
            <strong>{history.symbol} · archived 1-minute OHLC</strong>
            <span className={isStale?"text-amber-300":"text-slate-300"}>{isStale?"Historical / not current":"Recent archived data"}</span>
          </div>
          <CandleChart candles={history.candles}/>
          <p className="mt-2 text-xs text-slate-400">Source: {history.source} · {history.count} completed bars · last closed: {lastTs?new Date(lastTs).toLocaleString():"unknown"}</p>
          <p className="mt-1 text-xs text-amber-300">R2 is archived market history, not a live quote. Its price is never used for placing paper or live orders.</p>
        </div>
        <div className="space-y-2 rounded border border-[#37312A] p-3 text-sm">
          <h3 className="font-semibold text-[#D4AF37]">Archived market context</h3>
          <p>Market: {history.symbol} ({history.asset_class})</p>
          <p>Archived latest close: {latest?.close??"—"}</p>
          <p>Bars available: {history.count}</p>
          <p>History feed: {history.source}</p>
          <p className="text-xs text-slate-400">These archived candles support retrospective analysis. Collectors and training jobs must independently run for R2 to keep growing and AI models to learn from new data.</p>
        </div>
      </div>}
      <div className="space-y-2">
        <h3 className="font-semibold text-[#D4AF37]">R2 model forecast history</h3>
        {!signals.length&&<p className="text-sm text-slate-400">No trained-model forecasts are recorded for this market.</p>}
        <div className="grid gap-2 md:grid-cols-2">
          {signals.slice(0,6).map(s=><article key={s.id} className="rounded border border-[#38332B] p-3 text-xs">
            <p className="font-semibold">{s.symbol} · {s.bias} · {s.horizon_seconds}s</p>
            <p className="mt-1 text-slate-300">P(up): {Number(s.prob_up*100).toFixed(1)}% · {s.model_validation_status}</p>
            <p className="mt-1 text-slate-400">Source: {s.source} · {s.data_status} · {s.outcome_status}</p>
            <p className="mt-1 text-amber-300">No execution: {(s.block_reasons||[]).join(", ")}</p>
          </article>)}
        </div>
      </div>
      <p className="text-xs text-slate-400">Signals are model research only. A forecast is not a broker trade, predicted win rate, or authorization to submit a paper order.</p>
    </>}
  </section>;
}
