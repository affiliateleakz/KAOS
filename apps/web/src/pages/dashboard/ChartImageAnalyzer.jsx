import React, { useState } from "react";
import { api, errMsg } from "../../lib/api";

const input = "w-full rounded border border-[#4B4334] bg-[#080808] px-3 py-2 text-sm text-white";

export default function ChartImageAnalyzer() {
  const [file, setFile] = useState(null);
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (event) => {
    event.preventDefault();
    setError(""); setData(null);
    if (!file) { setError("Choose a chart image."); return; }
    if (!["image/png","image/jpeg","image/webp"].includes(file.type) || file.size > 4 * 1024 * 1024) {
      setError("Upload a PNG, JPEG or WebP chart screenshot smaller than 4 MB.");
      return;
    }
    const form = new FormData();
    form.append("image", file);
    form.append("symbol", symbol.trim().toUpperCase());
    form.append("timeframe", timeframe.trim());
    setBusy(true);
    try {
      const result = await api.post("/api/v1/ai/chart-analyze", form);
      setData(result.data);
    } catch (exc) {
      setError(errMsg(exc) || "Chart analysis is not available.");
    } finally { setBusy(false); }
  };
  const analysis = data?.analysis;
  return <section className="card-surface mt-6 p-5 space-y-4" data-testid="kaos-ai-chart-analyzer">
    <div>
      <h3 className="font-heading font-semibold text-[#D4AF37]">KAOS AI Chart Analyzer</h3>
      <p className="mt-1 text-sm text-slate-400">
        Upload a chart screenshot to identify visible patterns and possible bullish/bearish scenarios.
        This owner-only beta uses an external AI vision provider. Screenshots are not saved by KAOS.
      </p>
    </div>
    <form onSubmit={run} className="space-y-3">
      <label className="block text-sm">Chart screenshot (PNG / JPEG / WebP, max 4 MB)
        <input className="mt-1 block w-full text-sm text-slate-300" type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={e => {setFile(e.target.files?.[0] || null);setData(null);}} />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-xs text-slate-300">Market symbol (optional)
          <input className={"mt-1 " + input} maxLength={32} placeholder="BTC-USD, AAPL…"
            value={symbol} onChange={e => setSymbol(e.target.value)} />
        </label>
        <label className="block text-xs text-slate-300">Chart timeframe (optional)
          <input className={"mt-1 " + input} maxLength={40} placeholder="5m, 1h, 1d…"
            value={timeframe} onChange={e => setTimeframe(e.target.value)} />
        </label>
      </div>
      <button type="submit" disabled={busy || !file}
        className="rounded bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40">
        {busy ? "Analyzing chart…" : "Analyze chart"}
      </button>
    </form>
    <p className="text-xs text-amber-300">
      A screenshot is not live market data. Remove account numbers and personal information before upload.
      Analysis cannot place an order, calculate a validated win probability, or guarantee direction.
    </p>
    {error && <p role="alert" className="rounded border border-red-700 p-3 text-sm text-red-300">{error}</p>}
    {analysis && <div className="space-y-3 rounded border border-[#4B4334] p-4" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong className="text-[#D4AF37]">Visual assessment: {analysis.directional_bias}</strong>
        <span className="text-xs text-slate-400">Unverified static-image assessment</span>
      </div>
      <p className="text-sm"><b>Visible trend:</b> {analysis.trend}</p>
      <p className="text-sm"><b>Market shown:</b> {analysis.visible_symbol || "Unknown"} · <b>Timeframe:</b> {analysis.visible_timeframe || "Unknown"}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div><h4 className="text-sm font-semibold text-green-300">Bullish scenario</h4><p className="text-sm">{analysis.bullish_scenario}</p></div>
        <div><h4 className="text-sm font-semibold text-red-300">Bearish scenario</h4><p className="text-sm">{analysis.bearish_scenario}</p></div>
      </div>
      <p className="text-sm"><b>Invalidation:</b> {analysis.invalidation}</p>
      <p className="text-sm"><b>Patterns:</b> {analysis.visible_patterns?.join(", ") || "None verified"}</p>
      <p className="text-sm"><b>Support:</b> {analysis.support_levels?.join(", ") || "Not readable"}</p>
      <p className="text-sm"><b>Resistance:</b> {analysis.resistance_levels?.join(", ") || "Not readable"}</p>
      <p className="text-xs text-amber-300">Limitations: {analysis.limitations?.join("; ") || "Image-only analysis"}.</p>
      <p className="text-xs text-slate-400">{data.note}</p>
    </div>}
  </section>;
}
