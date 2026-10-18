import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { toast } from "sonner";
import { Activity, ShieldCheck, ShieldX } from "lucide-react";

const field = "w-full rounded border border-[#2E2E2E] bg-[#080808] px-3 py-2 font-mono text-sm text-white";
const ema = (vals, span) => { const k = 2 / (span + 1); let e = null; return vals.map((v) => (e = e == null ? v : v * k + e * (1 - k))); };

function CandleChart({ candles, quote, fills }) {
  const W = 900, H = 320, P = 8;
  const view = candles.slice(-90);
  if (!view.length) return <div className="flex h-[320px] items-center justify-center text-slate-500">Loading market data…</div>;
  const closes = candles.map((c) => c.close);
  const e20 = ema(closes, 20).slice(-view.length), e50 = ema(closes, 50).slice(-view.length);
  const hi = Math.max(...view.map((c) => c.high), quote ? Number(quote.ask) : 0);
  const lo = Math.min(...view.map((c) => c.low), quote ? Number(quote.bid) : Infinity);
  const y = (v) => P + (hi - v) / (hi - lo || 1) * (H - 2 * P);
  const step = (W - 60) / view.length, bw = Math.max(1, step * 0.6);
  const x = (i) => i * step + step / 2;
  const line = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const t0 = view[0].time;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-[320px] w-full" role="img" aria-label="Live candlestick chart" data-testid="paper-chart">
      {view.map((c, i) => {
        const up = c.close >= c.open, col = up ? "#22C55E" : "#EF4444";
        return (<g key={c.time}><line x1={x(i)} x2={x(i)} y1={y(c.high)} y2={y(c.low)} stroke={col} />
          <rect x={x(i) - bw / 2} width={bw} y={y(Math.max(c.open, c.close))} height={Math.max(1, Math.abs(y(c.open) - y(c.close)))} fill={col} /></g>);
      })}
      <path d={line(e20)} fill="none" stroke="#2F8CFF" strokeWidth="1.5" />
      <path d={line(e50)} fill="none" stroke="#C0C7D1" strokeWidth="1.2" strokeDasharray="4 3" />
      {fills.filter((f) => f.t >= t0).map((f, i) => {
        const idx = Math.min(view.length - 1, Math.floor((f.t - t0) / (view[1] ? view[1].time - t0 : 60)));
        return <text key={i} x={x(idx)} y={y(f.price) + (f.side === "BUY" ? 16 : -8)} textAnchor="middle" fontSize="13" fill={f.side === "BUY" ? "#22C55E" : "#EF4444"}>{f.side === "BUY" ? "▲" : "▼"}</text>;
      })}
      {quote && <g><line x1="0" x2={W - 60} y1={y(Number(quote.ask))} y2={y(Number(quote.ask))} stroke="#7DB8FF" strokeDasharray="2 3" />
        <text x={W - 56} y={y(Number(quote.ask)) + 4} fontSize="11" fill="#7DB8FF" fontFamily="monospace">{Number(quote.ask).toFixed(2)}</text></g>}
      <text x={W - 56} y={14} fontSize="10" fill="#94A3B8" fontFamily="monospace">{hi.toFixed(2)}</text>
      <text x={W - 56} y={H - 4} fontSize="10" fill="#94A3B8" fontFamily="monospace">{lo.toFixed(2)}</text>
    </svg>
  );
}

export default function PaperSession({ orders, killSwitch, onTraded }) {
  const [brokers, setBrokers] = useState([]);
  const [session, setSession] = useState(null);
  const [candles, setCandles] = useState({ candles: [] });
  const [quote, setQuote] = useState(null);
  const [signals, setSignals] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadSignals = useCallback(() => api.get("/api/v1/paper/signals").then((r) => setSignals(r.data.signals)).catch(() => {}), []);
  useEffect(() => {
    api.get("/api/v1/paper/brokers").then((r) => setBrokers(r.data.brokers)).catch((e) => toast.error(errMsg(e)));
    api.get("/api/v1/paper/session").then((r) => setSession(r.data)).catch((e) => toast.error(errMsg(e)));
    loadSignals();
  }, [loadSignals]);

  const sym = session?.symbol, gran = session?.granularity;
  useEffect(() => {
    if (!sym) return undefined;
    let live = true;
    const pullC = () => api.get(`/api/v1/paper/candles/${encodeURIComponent(sym)}?granularity=${gran}`).then((r) => live && setCandles(r.data)).catch((e) => live && setCandles({ candles: [], error: errMsg(e) }));
    const pullQ = () => api.get(`/api/v1/paper/quote/${encodeURIComponent(sym)}`).then((r) => live && setQuote(r.data)).catch(() => live && setQuote(null));
    pullC(); pullQ();
    const a = setInterval(pullC, 15000), b = setInterval(pullQ, 5000);
    return () => { live = false; clearInterval(a); clearInterval(b); };
  }, [sym, gran]);

  const save = async (patch) => {
    const next = { ...session, ...patch };
    setSession(next);
    try { setSession((await api.put("/api/v1/paper/session", { broker: next.broker, symbol: next.symbol, granularity: Number(next.granularity), notional: next.notional, fee_rate: String(next.fee_rate ?? "0.006"), slippage_bps: Number(next.slippage_bps || 0) })).data); }
    catch (e) { toast.error(errMsg(e)); }
  };

  const runStrategy = async () => {
    setBusy(true);
    try { await api.post(`/api/v1/paper/signals/${encodeURIComponent(sym)}?granularity=${gran}`, { notional: session.notional }); }
    catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); loadSignals(); }
  };
  const execute = async (id) => {
    setBusy(true);
    try { const r = await api.post(`/api/v1/paper/signals/${id}/execute`); toast.success(`Paper ${r.data.side} filled at ${r.data.fill_price} (fee $${Number(r.data.fee).toFixed(2)})`); }
    catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); loadSignals(); onTraded(); }
  };

  const fills = useMemo(() => (orders || []).filter((o) => o.symbol === sym && o.execution_kind === "market_data_paper")
    .map((o) => ({ t: Date.parse(o.created_at) / 1000, price: Number(o.fill_price), side: o.side })), [orders, sym]);
  if (!session) return <div className="card-surface mb-6 p-5 text-slate-500">Loading session…</div>;
  const latest = signals[0];
  const stepCls = (ok) => `rounded px-2 py-0.5 text-[10px] font-mono ${ok ? "bg-[#2F8CFF]/15 text-[#7DB8FF]" : "bg-[#1A1A1A] text-slate-500"}`;

  return (
    <div className="card-surface mb-6 p-5" data-testid="paper-session">
      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
        <span className={stepCls(true)}>1 BROKER</span><span className={stepCls(candles.candles.length > 0)}>2 MARKET DATA</span>
        <span className={stepCls(!!latest)}>3 STRATEGY SIGNAL</span><span className={stepCls(!!latest?.risk)}>4 RISK CHECK</span>
        <span className={stepCls(latest?.status === "EXECUTED")}>5 PAPER FILL</span><span className={stepCls(fills.length > 0)}>6 PORTFOLIO + JOURNAL</span>
      </div>
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <label className="block"><span className="label-mono">Broker</span>
          <select data-testid="paper-broker" className={field} value={session.broker} onChange={(e) => save({ broker: e.target.value })}>
            {brokers.map((b) => <option key={b.id} value={b.id} disabled={!b.available}>{b.name}{b.available ? "" : " (unavailable)"}</option>)}
          </select></label>
        <label className="block"><span className="label-mono">Market</span>
          <input data-testid="paper-session-symbol" className={field} defaultValue={session.symbol} onBlur={(e) => e.target.value.toUpperCase() !== session.symbol && save({ symbol: e.target.value.toUpperCase() })} /></label>
        <label className="block"><span className="label-mono">Candles</span>
          <select className={field} value={session.granularity} onChange={(e) => save({ granularity: Number(e.target.value) })}><option value={60}>1 min</option><option value={300}>5 min</option><option value={900}>15 min</option></select></label>
        <label className="block"><span className="label-mono">Trade size (USD)</span>
          <input className={field} type="number" min="1" step="1" defaultValue={session.notional} onBlur={(e) => e.target.value !== session.notional && save({ notional: e.target.value })} /></label>
      </div>
      <div className="mb-3 grid gap-3 md:grid-cols-4">
        <label className="block"><span className="label-mono">Sim. fee % per side</span>
          <input data-testid="paper-fee" className={field} type="number" min="0" max="2" step="0.01" defaultValue={(Number(session.fee_rate ?? 0.006) * 100).toFixed(2)} onBlur={(e) => save({ fee_rate: String(Number(e.target.value) / 100) })} /></label>
        <label className="block"><span className="label-mono">Sim. slippage (bps)</span>
          <input data-testid="paper-slippage" className={field} type="number" min="0" max="100" step="1" defaultValue={session.slippage_bps || 0} onBlur={(e) => save({ slippage_bps: Number(e.target.value) })} /></label>
        <p className="text-[11px] text-slate-500 md:col-span-2 md:self-end">Fee and slippage are illustrative research assumptions you set, not Coinbase or broker quotes. The spread comes from the live bid/ask; slippage is applied on top of it. Limits: fee 0–2%, slippage 0–100 bps.</p>
      </div>
      <p className="mb-2 text-xs text-slate-500">{brokers.find((b) => b.id === session.broker)?.note} Unavailable: {brokers.filter((b) => !b.available).map((b) => `${b.name}: ${b.note}`).join(" ")}</p>
      <div className="rounded border border-[#2E2E2E] bg-[#050505] p-2">
        <div className="flex items-center justify-between px-2 pb-1 font-mono text-xs text-slate-400">
          <span><Activity className="mr-1 inline h-3 w-3 text-[#2F8CFF]" />{sym} · {gran / 60}m · <span className="text-[#2F8CFF]">EMA20</span> / <span className="text-slate-300">EMA50</span></span>
          <span data-testid="paper-session-quote">{quote ? <>bid {quote.bid} · ask {quote.ask} · quote {quote.quote_time?.slice(11, 19)} UTC · <span className={quote.age_seconds > quote.max_age_seconds ? "text-amber-300" : ""}>age {quote.age_seconds}s</span> · {quote.delivery} · {quote.source}</> : "no quote (orders are refused without a fresh quote)"}</span>
        </div>
        {candles.error ? <div className="p-6 text-sm text-red-300">{candles.error}</div> : <CandleChart candles={candles.candles} quote={quote} fills={fills} />}
        <div className="px-2 font-mono text-[10px] text-slate-500">Source: {candles.source || "—"} · closed candles only · polled every 15 s (not streaming)</div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Button data-testid="paper-run-strategy" onClick={runStrategy} disabled={busy || killSwitch} className="w-full bg-[#2F8CFF] font-semibold text-black hover:bg-[#7DB8FF]">Run KAOS Strategy</Button>
          <p className="text-[11px] text-slate-500">KAOS Structure v2 on the last closed candle. Unvalidated research strategy (v2.1 archival audit: FAIL). Paper only; AI-controlled execution stays locked.</p>
        </div>
        <div className="rounded border border-[#2E2E2E] p-3 text-sm md:col-span-2" data-testid="paper-latest-signal">
          {!latest ? <span className="text-slate-500">No signal yet.</span> : (
            <>
              <div className="flex items-center justify-between"><span className="font-mono"><b className={latest.action === "BUY" ? "text-[#22C55E]" : latest.action === "SELL" ? "text-red-400" : "text-slate-300"}>{latest.action}</b> {latest.symbol} · {latest.setup}</span>
                <span className="font-mono text-[10px] text-slate-500">{latest.created_at?.slice(11, 19)} UTC · {latest.status}</span></div>
              <ul className="mt-1 list-disc pl-5 text-xs text-slate-300">{latest.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              <div className={`mt-2 flex items-start gap-1 text-xs ${latest.risk.approved ? "text-[#7DB8FF]" : "text-amber-300"}`}>{latest.risk.approved ? <ShieldCheck className="h-4 w-4 shrink-0" /> : <ShieldX className="h-4 w-4 shrink-0" />}Risk manager {latest.risk.approved ? "approved" : "rejected"}: {latest.risk.reason}</div>
              {latest.status === "PENDING" && <Button data-testid="paper-execute-signal" size="sm" disabled={busy || killSwitch} onClick={() => execute(latest.signal_id)} className="mt-2 bg-[#22C55E] text-black">Execute paper trade at market</Button>}
              {latest.risk_at_execution && <div className={`mt-1 text-xs ${latest.risk_at_execution.approved ? "text-[#7DB8FF]" : "text-red-300"}`}>Risk re-check at execution: {latest.risk_at_execution.approved ? "approved" : "rejected"}: {latest.risk_at_execution.reason}</div>}
            </>
          )}
        </div>
      </div>
      {signals.length > 1 && (
        <details className="mt-3 text-xs text-slate-400"><summary className="cursor-pointer">Signal journal ({signals.length})</summary>
          <ul className="mt-2 space-y-1 font-mono">{signals.map((s) => <li key={s.signal_id}>{s.created_at?.slice(0, 19).replace("T", " ")} · {s.symbol} · {s.action} · {s.setup} · risk {s.risk.approved ? "ok" : "rejected"} · {s.status}</li>)}</ul></details>
      )}
    </div>
  );
}
