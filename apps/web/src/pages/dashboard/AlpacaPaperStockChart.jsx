import React,{useCallback,useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";
import {CandleChart} from "./FourChartTerminal";

// Reuses the same KAOS candlestick renderer as the Trading Bot terminal.
// The chart contains only actual provider bars; it never generates candles.
export default function AlpacaPaperStockChart({symbol}){
  const [seconds,setSeconds]=useState(60);
  const [record,setRecord]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const ticker=(symbol||"").trim().toUpperCase();
  const load=useCallback(async()=>{
    if(!/^[A-Z]{1,5}(?:[.][A-Z])?$/.test(ticker)){
      setRecord(null);setError("Enter a valid US stock ticker");return;
    }
    setLoading(true);
    try{
      const {data}=await api.get("/api/v1/alpaca-paper/candles/"+encodeURIComponent(ticker),{params:{seconds}});
      if(!Array.isArray(data?.candles))throw Error("Invalid stock data");
      setRecord(data);setError("");
    }catch(e){setRecord(null);setError(errMsg(e)||"Alpaca IEX candles unavailable");}
    finally{setLoading(false);}
  },[ticker,seconds]);
  useEffect(()=>{load();const timer=setInterval(()=>{if(!document.hidden)load();},30000);
    return()=>clearInterval(timer);},[load]);
  return <section className="rounded border border-[#48402E] bg-[#0A0A0A] p-3 space-y-2" data-testid="alpaca-paper-stock-chart">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <strong>{ticker||"Select stock"} · Alpaca IEX chart</strong>
      <div className="flex items-center gap-2">
        <select aria-label="Alpaca paper stock timeframe" className="rounded bg-[#222] p-2 text-xs" value={seconds} onChange={e=>setSeconds(Number(e.target.value))}>
          <option value={60}>1 min</option><option value={300}>5 min</option><option value={900}>15 min</option>
        </select>
        <button type="button" className="rounded border border-[#D4AF37] px-2 py-1 text-xs text-[#D4AF37]" onClick={load}>Refresh</button>
      </div>
    </div>
    {error?<p role="status" className="text-xs text-amber-300">{error}</p>:<CandleChart candles={record?.candles}/>}
    <p className="text-xs text-slate-400">
      {loading?"Updating · ":""}Source: {record?.source||"Unavailable"} · {record?.candles?.length||0} completed candles
      {record?.last_closed_bar_time?" · last closed "+record.last_closed_bar_time:""}
    </p>
    <p className="text-xs text-amber-300">IEX is a limited market feed; the chart may have gaps. Alpaca paper execution prices may differ from the candles and preview quote.</p>
  </section>;
}
