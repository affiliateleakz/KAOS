import React,{useState} from "react";
import {api,errMsg} from "../../lib/api";

function readCandles(text,label){
 const data=JSON.parse(text);
 if(!Array.isArray(data))throw Error(label+" must be a JSON array");
 return data.map((row,i)=>{
  if(!row||typeof row!=="object")throw Error(label+" row "+i+" is not an object");
  const ts=Number(row.ts),open=Number(row.open),high=Number(row.high),low=Number(row.low),close=Number(row.close);
  if(![ts,open,high,low,close].every(Number.isFinite))throw Error(label+" row "+i+" contains invalid OHLC or timestamp");
  return {ts,open,high,low,close};
 });
}
export default function TrendPauseBacktest(){
 const [minutes,setMinutes]=useState(""),[seconds,setSeconds]=useState(""),[horizon,setHorizon]=useState("60");
 const [result,setResult]=useState(null),[error,setError]=useState(""),[loading,setLoading]=useState(false);
 const importFile=async (event,setter)=>{
  const file=event.target.files?.[0];
  if(!file)return;
  try{
   if(file.size>2500000)throw Error("JSON file exceeds the 2.5 MB limit");
   const content=await file.text();
   readCandles(content,"Uploaded");
   setter(content);setError("");setResult(null);
  }catch(e){setError(e.message||"File could not be read");}
  finally{event.target.value="";}
 };
 const run=async e=>{
  e.preventDefault();setResult(null);setError("");setLoading(true);
  try{
   const payload={minute_candles:readCandles(minutes,"1-minute"),fifteen_second_candles:readCandles(seconds,"15-second"),horizon_seconds:Number(horizon)};
   const response=await api.post("/api/v1/research/trend-pause/replay",payload);
   setResult(response.data);
  }catch(e){setError(e instanceof SyntaxError?"Invalid JSON input.":errMsg(e)||e.message);}
  finally{setLoading(false)}
 };
 return <section className="card-surface p-5 space-y-4" data-testid="trend-pause-backtest">
   <h2 className="font-heading text-lg font-bold">KAOS Trend-Pause Backtest · Historical Research</h2>
   <p className="text-xs text-slate-400">Paste real chronological candle arrays containing ts (Unix seconds), open, high, low and close. One-minute and 15-second data must refer to the same market and period. No synthetic candles or broker orders.</p>
   <form onSubmit={run} className="space-y-3">\n    <div className="grid gap-3 md:grid-cols-2">\n      <label className="text-xs">Import 1-minute JSON file<input type="file" accept=".json,application/json" onChange={e=>importFile(e,setMinutes)} className="mt-1 block w-full text-xs"/></label>\n      <label className="text-xs">Import 15-second JSON file<input type="file" accept=".json,application/json" onChange={e=>importFile(e,setSeconds)} className="mt-1 block w-full text-xs"/></label>\n    </div>
     <div className="grid gap-3 md:grid-cols-2">
      <label className="text-sm">1-minute candles (at least 53)<textarea value={minutes} onChange={e=>setMinutes(e.target.value)} required rows={5} spellCheck={false} placeholder='[{"ts":1760000000,"open":1,"high":2,"low":1,"close":2}]' className="mt-1 w-full rounded border border-[#333] bg-[#0c0c0c] p-2 font-mono text-xs"/></label>
      <label className="text-sm">15-second candles (at least 24)<textarea value={seconds} onChange={e=>setSeconds(e.target.value)} required rows={5} spellCheck={false} placeholder='[{"ts":1760000000,"open":1,"high":2,"low":1,"close":2}]' className="mt-1 w-full rounded border border-[#333] bg-[#0c0c0c] p-2 font-mono text-xs"/></label>
     </div>
     <label className="block text-sm">Expiry / exit horizon<select value={horizon} onChange={e=>setHorizon(e.target.value)} className="ml-2 rounded border border-[#333] bg-[#111] p-2">{[15,30,60,120,300,900].map(s=><option key={s} value={s}>{s}s</option>)}</select></label>
     <button disabled={loading} type="submit" className="rounded bg-[#2F8CFF] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40">{loading?"Running replay…":"Run Historical Backtest"}</button>
   </form>
   {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
   {result&&<div aria-live="polite" className="rounded border border-[#333] p-3 text-sm">
    <p className="font-semibold">Research only · no executable trading signal</p>
    <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">{JSON.stringify(result,null,2)}</pre>
   </div>}
 </section>;
}
