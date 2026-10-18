import ReplayTradeChart from "./ReplayTradeChart";
import React,{useState} from "react";
import {api,errMsg} from "../../lib/api";

function readCandles(text,label){
 const data=JSON.parse(text);
 if(!Array.isArray(data))throw Error(label+" must be a JSON array");
 const converted=data.map((row,i)=>{
  if(!row||typeof row!=="object")throw Error(label+" row "+i+" is not an object");
  const ts=Number(row.ts),open=Number(row.open),high=Number(row.high),low=Number(row.low),close=Number(row.close);
  if(!Number.isSafeInteger(ts)||ts<1000000000000||ts>9999999999999)throw Error(label+" row "+i+" requires a Unix millisecond timestamp");
  if(![ts,open,high,low,close].every(Number.isFinite))throw Error(label+" row "+i+" contains invalid OHLC or timestamp");
  if(Math.min(open,high,low,close)<=0 || low>Math.min(open,close) || high<Math.max(open,close) || high<low)throw Error(label+" row "+i+" has invalid OHLC range");
  return {ts,open,high,low,close};
 });
 for(let i=1;i<converted.length;i++)if(converted[i].ts<=converted[i-1].ts)throw Error(label+" timestamp order or duplicate at row "+(i+1));
 return converted;
}
function candleDiagnostics(text,label,period){
 try{
  if(!text.trim())return null;
  const candles=readCandles(text,label);
  if(candles.length===0)return {error:"No candle rows found"};
  let gaps=0;
  for(let i=1;i<candles.length;i++)if(candles[i].ts-candles[i-1].ts!==period)gaps++;
  const alignment=candles.filter(c=>c.ts%period!==0).length;
  return {count:candles.length,gaps,alignment,start:new Date(candles[0].ts).toISOString(),end:new Date(candles[candles.length-1].ts).toISOString()};
 }catch(e){return {error:e.message}}
}
function csvToCandleJson(text){
 const lines=text.replace(/^\uFEFF/,"").trim().split(/\r?\n/).filter(Boolean);
 if(lines.length<2)throw Error("CSV needs a header and candle rows");
 const headers=lines.shift().split(",").map(h=>h.trim().toLowerCase());
 const keys=["ts","open","high","low","close"];
 const index=keys.map(k=>headers.indexOf(k));
 if(index.some(i=>i<0))throw Error("CSV headers must include ts,open,high,low,close");
 const rows=lines.map((line,i)=>{
  const fields=line.split(",").map(x=>x.trim());
  if(fields.length!==headers.length)throw Error("CSV row "+(i+2)+" has the wrong column count");
  return Object.fromEntries(keys.map((k,j)=>[k,fields[index[j]]]));
 });
 return JSON.stringify(rows);
}
export default function TrendPauseBacktest(){
 const [minutes,setMinutes]=useState(""),[seconds,setSeconds]=useState(""),[horizon,setHorizon]=useState("60"),[strategy,setStrategy]=useState("trend-pause");
 const [result,setResult]=useState(null),[error,setError]=useState(""),[loading,setLoading]=useState(false);
 const datasets=[["1-minute",minutes,60000],["15-second",seconds,15000]];
 const diagnostics=datasets.map(([label,value,period])=>({label,info:candleDiagnostics(value,label,period)}));
 const importFile=async (event,setter)=>{
  const file=event.target.files?.[0];
  if(!file)return;
  try{
   if(file.size>2500000)throw Error("File exceeds the 2.5 MB limit");
   const content=await file.text();
   const normalized=file.name.toLowerCase().endsWith(".csv")?csvToCandleJson(content):content;
   readCandles(normalized,"Uploaded");
   setter(normalized);setError("");setResult(null);
  }catch(e){setError(e.message||"File could not be read");}
  finally{event.target.value="";}
 };
 const run=async e=>{
  e.preventDefault();setResult(null);setError("");setLoading(true);
  try{
   const payload=strategy==="structure"?{candles:readCandles(seconds,"Research candles"),expiry_bars:Number(horizon)/15,lookback:12}:{minute_candles:readCandles(minutes,"1-minute"),fifteen_second_candles:readCandles(seconds,"15-second"),horizon_seconds:Number(horizon)};
   const endpoint=strategy==="structure"?"/api/v1/research/structure/replay":"/api/v1/research/trend-pause/replay";
   const response=await api.post(endpoint,payload);
   setResult(response.data);
  }catch(e){setError(e instanceof SyntaxError?"Invalid JSON input.":errMsg(e)||e.message);}
  finally{setLoading(false)}
 };
 return <section className="card-surface p-5 space-y-4" data-testid="trend-pause-backtest">
   <h2 className="font-heading text-lg font-bold">KAOS Backtest Lab · Historical Research</h2>
   <label className="block text-sm">Strategy <select value={strategy} onChange={e=>{setStrategy(e.target.value);setResult(null);}} className="ml-2 rounded border border-[#333] bg-[#111] p-2"><option value="trend-pause">Trend-Pause (1m + 15s)</option><option value="structure">Price action (15s candles)</option></select></label>
   <p className="text-xs text-slate-400">Paste real chronological candle arrays containing ts (Unix milliseconds), open, high, low and close. One-minute and 15-second data must refer to the same market and period. No synthetic candles or broker orders.</p>
   <div className="grid gap-2 md:grid-cols-2">
    {diagnostics.map(({label,info})=><div key={label} className="rounded border border-[#333] p-3 text-xs">
     <p className="font-semibold">{label} dataset</p>
     {!info?<p className="text-slate-400">No candles loaded</p>:info.error?<p role="alert" className="text-red-400">{info.error}</p>:<>
      <p>{info.count} candles · {info.gaps} time gaps · {info.alignment} misaligned bars</p>
      <p className="text-slate-400">{info.start} → {info.end}</p>
      {(info.gaps>0||info.alignment>0)&&<p className="text-amber-300">Fix data gaps or alignment before interpreting replay results.</p>}
     </>}
    </div>)}
   </div>
   <form onSubmit={run} className="space-y-3">\n    <div className="grid gap-3 md:grid-cols-2">\n      <label className="text-xs">Import 1-minute JSON or CSV<input type="file" accept=".json,.csv,application/json,text/csv" onChange={e=>importFile(e,setMinutes)} className="mt-1 block w-full text-xs"/></label>\n      <label className="text-xs">Import 15-second JSON or CSV<input type="file" accept=".json,.csv,application/json,text/csv" onChange={e=>importFile(e,setSeconds)} className="mt-1 block w-full text-xs"/></label>\n    </div>
     <div className="grid gap-3 md:grid-cols-2">
      <label className="text-sm">1-minute candles (Trend-Pause only, at least 53)<textarea value={minutes} onChange={e=>setMinutes(e.target.value)} required rows={5} spellCheck={false} placeholder='[{"ts":1760054400000,"open":1,"high":2,"low":1,"close":2}]' className="mt-1 w-full rounded border border-[#333] bg-[#0c0c0c] p-2 font-mono text-xs"/></label>
      <label className="text-sm">15-second candles (at least 24)<textarea value={seconds} onChange={e=>setSeconds(e.target.value)} required rows={5} spellCheck={false} placeholder='[{"ts":1760054400000,"open":1,"high":2,"low":1,"close":2}]' className="mt-1 w-full rounded border border-[#333] bg-[#0c0c0c] p-2 font-mono text-xs"/></label>
     </div>
     <label className="block text-sm">Expiry / exit horizon<select value={horizon} onChange={e=>setHorizon(e.target.value)} className="ml-2 rounded border border-[#333] bg-[#111] p-2">{[15,30,60,120,300,900].map(s=><option key={s} value={s}>{s}s</option>)}</select></label>
     <button disabled={loading} type="submit" className="rounded bg-[#2F8CFF] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40">{loading?"Running replay…":"Run Historical Backtest"}</button>
   </form>
   {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
   {result&&<div aria-live="polite" className="rounded border border-[#333] p-3 text-sm">
    <p className="font-semibold">Research only · no executable trading signal</p>
    <ReplayTradeChart candles={readCandles(seconds,"15-second")} trades={result.trades||[]} />
    <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
     {[
      ["Trades",result.summary?.trades],["Wins",result.summary?.wins],["Losses",result.summary?.losses],
      ["Ties",result.summary?.ties],["Win rate (ex ties)",result.summary?.win_rate_ex_ties==null?"—":result.summary.win_rate_ex_ties+"%"],
      ["Trades/hour",result.summary?.trades_per_hour??"—"],["Data hours",result.summary?.data_hours??"—"]
     ].map(([label,value])=><div key={label} className="rounded bg-[#151515] p-3">
      <p className="text-xs text-slate-400">{label}</p><p className="mt-1 font-mono text-lg">{value??"—"}</p>
     </div>)}
    </div>
    <p className="mt-3 text-xs text-amber-300">Directional results only: no fees, spread, slippage, payout or profitability calculation. No historical performance guarantee.</p>
    <div className="mt-3 max-h-80 overflow-auto">
     <table className="w-full min-w-[650px] text-left text-xs">
      <thead><tr className="border-b border-[#333] text-slate-400">
       <th className="p-2">Entry (UTC)</th><th className="p-2">Direction</th><th className="p-2">Entry</th>
       <th className="p-2">Exit (UTC)</th><th className="p-2">Exit</th><th className="p-2">Outcome</th>
      </tr></thead>
      <tbody>{(result.trades||[]).map((trade,i)=><tr key={i} className="border-b border-[#222]">
       <td className="p-2">{new Date(trade.entry_ts).toISOString()}</td>
       <td className="p-2">{trade.direction}</td><td className="p-2 font-mono">{trade.entry_price}</td>
       <td className="p-2">{new Date(trade.exit_ts).toISOString()}</td><td className="p-2 font-mono">{trade.exit_price}</td>
       <td className={"p-2 font-semibold "+(trade.outcome==="WIN"?"text-green-400":trade.outcome==="LOSS"?"text-red-400":"text-slate-400")}>{trade.outcome}</td>
      </tr>)}</tbody>
     </table>
     {!result.trades?.length&&<p className="p-3 text-slate-400">No qualifying trades in this historical sample.</p>}
    </div>
    <details className="mt-3"><summary className="cursor-pointer text-xs text-slate-400">Raw backtest JSON</summary>
     <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">{JSON.stringify(result,null,2)}</pre>
    </details>
   </div>}
 </section>;
}
