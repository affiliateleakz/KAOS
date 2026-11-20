import React, {useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";

export default function ChartSnapshotAnalyzer() {
  const [preview,setPreview]=useState("");
  const [symbol,setSymbol]=useState("BTC-USD");
  const [seconds,setSeconds]=useState("60");
  const [assetClass,setAssetClass]=useState("crypto");
  const [busy,setBusy]=useState("");
  const [error,setError]=useState("");
  const [analysis,setAnalysis]=useState(null);
  const [matches,setMatches]=useState(null);

  function loadFile(file) {
    if (!file) return;
    setError("");setAnalysis(null);
    if (!["image/png","image/jpeg","image/webp"].includes(file.type)) {
      setError("Choose a PNG, JPEG, or WebP screenshot.");return;
    }
    if (file.size>1500000) {setError("Screenshot must be under 1.5 MB.");return;}
    const reader=new FileReader();
    reader.onload=()=>setPreview(String(reader.result||""));
    reader.onerror=()=>setError("Could not read the image.");
    reader.readAsDataURL(file);
  }
  useEffect(()=>{
    const pasted=e=>{
      const file=Array.from(e.clipboardData?.files||[]).find(x=>x.type.startsWith("image/"));
      if (file) {e.preventDefault();loadFile(file);}
    };
    window.addEventListener("paste",pasted);
    return ()=>window.removeEventListener("paste",pasted);
  },[]);

  async function analyze() {
    if (!preview) {setError("Upload or paste a chart screenshot first.");return;}
    setBusy("analyze");setError("");setAnalysis(null);
    try {
      const res=await api.post("/api/v1/ai/chart-snapshot/analyze", {
        image_data:preview,symbol:symbol.toUpperCase(),timeframe:seconds+"s"
      });
      setAnalysis(res.data);
    } catch(e) {setError(errMsg(e)||"Chart interpretation unavailable");}
    finally {setBusy("");}
  }
  async function findSimilar() {
    setBusy("similar");setError("");setMatches(null);
    try {
      const res=await api.get("/api/v1/ai/chart-snapshot/similar",{params:{
        symbol:symbol.toUpperCase(),seconds:Number(seconds),asset_class:assetClass,
        lookback:20,horizon:5
      }});
      setMatches(res.data);
    }catch(e){setError(errMsg(e)||"Historical comparison unavailable");}
    finally {setBusy("");}
  }
  const pct=n=>n==null?"—":(n*100).toFixed(2)+"%";
  return <section className="card-surface mt-6 p-5 space-y-4" data-testid="chart-snapshot-analyzer">
    <div>
      <h3 className="font-heading text-xl font-semibold text-[#D4AF37]">KAOS Chart Snapshot Analyzer</h3>
      <p className="mt-1 text-xs text-slate-400">Paste a chart image (Ctrl+V) or upload one. Visual analysis is educational; historical matching uses archived KAOS market candles, not pixels from your screenshot.</p>
    </div>
    <div className="grid gap-3 md:grid-cols-3">
      <label className="text-xs text-slate-300">Market symbol
        <input aria-label="Market symbol" value={symbol} onChange={e=>setSymbol(e.target.value.toUpperCase())}
          className="mt-1 w-full rounded border border-[#444] bg-black p-2"/>
      </label>
      <label className="text-xs text-slate-300">Asset class
        <select aria-label="Asset class" value={assetClass} onChange={e=>setAssetClass(e.target.value)}
          className="mt-1 w-full rounded border border-[#444] bg-black p-2">
          <option value="crypto">Crypto</option><option value="stock">Stock</option><option value="forex">Forex</option>
        </select>
      </label>
      <label className="text-xs text-slate-300">Archived candle interval
        <select aria-label="Archived candle interval" value={seconds} onChange={e=>setSeconds(e.target.value)}
          className="mt-1 w-full rounded border border-[#444] bg-black p-2">
          <option value="60">1 minute</option><option value="300">5 minutes</option><option value="900">15 minutes</option>
        </select>
      </label>
    </div>
    <label className="block rounded border border-dashed border-[#555] bg-[#090909] p-4 text-center text-sm text-slate-300">
      Select chart screenshot
      <input aria-label="Chart screenshot" className="mt-2 block w-full text-xs"
        type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>loadFile(e.target.files?.[0])}/>
    </label>
    {preview&&<img src={preview} alt="Uploaded chart preview" className="max-h-64 max-w-full rounded border border-[#444] object-contain"/>}
    <div className="flex flex-wrap gap-3">
      <button disabled={!!busy||!preview} onClick={analyze} className="rounded bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40">{busy==="analyze"?"Analyzing…":"Interpret screenshot"}</button>
      <button disabled={!!busy} onClick={findSimilar} className="rounded border border-[#D4AF37] px-4 py-2 text-sm text-[#D4AF37] disabled:opacity-40">{busy==="similar"?"Searching archive…":"Find historical patterns"}</button>
    </div>
    {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
    {analysis&&<div className="rounded border border-[#333] p-4 space-y-2" data-testid="chart-vision-result">
      <h4 className="font-semibold text-white">Screenshot interpretation</h4>
      <p className="whitespace-pre-wrap text-sm text-slate-200">{analysis.analysis}</p>
      <p className="text-xs text-amber-300">{analysis.note}</p>
    </div>}
    {matches&&<div className="rounded border border-[#333] p-4 space-y-2" data-testid="historical-chart-matches">
      <h4 className="font-semibold text-white">Historical pattern comparisons</h4>
      <p className="text-xs text-slate-400">{matches.count} nonoverlapping historical analogs found in {matches.archive_candles||0} archived candles. {matches.reason||matches.note}</p>
      {matches.count>0&&<>
        <p className="text-sm">Matched historical upward outcomes: {pct(matches.historical_up_fraction)} of {matches.count} matches (descriptive, not a calibrated prediction).</p>
        <div className="overflow-x-auto"><table className="w-full text-xs">
          <thead><tr><th className="p-2 text-left">Historical date</th><th className="p-2 text-left">Distance</th><th className="p-2 text-left">Subsequent return proxy</th></tr></thead>
          <tbody>{matches.matches.map(m=><tr className="border-t border-[#333]" key={m.decision_ms}>
            <td className="p-2">{new Date(m.decision_ms).toLocaleString()}</td>
            <td className="p-2">{m.distance}</td><td className="p-2">{pct(m.forward_return_proxy)}</td>
          </tr>)}</tbody>
        </table></div>
      </>}
    </div>}
    <p className="text-xs text-slate-500">No trades are placed. Chart screenshots are processed in memory and are not saved by KAOS. A separate vision provider processes screenshots when enabled.</p>
  </section>;
}
