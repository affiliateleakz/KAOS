import FourChartTerminal from "./FourChartTerminal";
import TrendPauseBacktest from "./TrendPauseBacktest";
import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Textarea } from "../../components/ui/textarea";
import { toast } from "sonner";
import { Bot, Brain, Layers, Lock, Cpu, Wifi, WifiOff, RefreshCw, Zap, Share2, Link as LinkIcon, LineChart } from "lucide-react";

const STATE_COLOR = {
  SIGNAL_GENERATED: "text-slate-300", SIGNAL_DELIVERED: "text-slate-300",
  ORDER_SUBMIT_ATTEMPT: "text-amber-300", BROKER_CONFIRMED: "text-[#2F8CFF]",
  TRADE_OPEN: "text-[#2F8CFF]", TRADE_RESULT: "text-white", ORDER_FAILED: "text-[#C62828]",
};
const MODE_META = {
  STRATEGY: { label: "Strategy", icon: Bot, desc: "Trade using the deterministic KAOS Strategy." },
  AI: { label: "AI", icon: Brain, desc: "Trade using KAOS AI predictions." },
  STRATEGY_AI: { label: "Strategy + AI", icon: Layers, desc: "Use both systems together." },
};

function relTime(iso) {
  if (!iso) return "never";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "never";
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

function SyncHealth({ sync, expired, onRefresh }) {
  if (expired) {
    return (
      <div data-testid="sync-health" className="card-surface mb-6 flex flex-wrap items-center gap-4 p-4">
        <div className="flex items-center gap-2 text-amber-300">
          <WifiOff className="h-5 w-5" />
          <span data-testid="sync-health-state" className="font-heading text-sm font-semibold">Session expired — sign in again</span>
        </div>
        <a href="/login" className="ml-auto text-xs text-[#2F8CFF] hover:underline">Sign in</a>
      </div>
    );
  }
  if (!sync) return null;
  const ok = sync.connected;
  return (
    <div data-testid="sync-health" className="card-surface mb-6 flex flex-wrap items-center gap-4 p-4">
      <div className={`flex items-center gap-2 ${ok ? "text-[#22C55E]" : "text-slate-400"}`}>
        {ok ? <Wifi className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
        <span data-testid="sync-health-state" className="font-heading text-sm font-semibold">{ok ? "Extension synced" : "Awaiting extension sync"}</span>
      </div>
      <div className="font-mono text-xs text-slate-400">Last event <span data-testid="sync-health-last" className="text-white">{relTime(sync.lastEventAt)}</span></div>
      <div className="font-mono text-xs text-slate-400">Confirmed trade <span className="text-white">{relTime(sync.lastConfirmedAt)}</span></div>
      <div className="font-mono text-xs text-slate-400">Events synced <span data-testid="sync-health-total" className="text-[#2F8CFF]">{sync.totalEvents}</span></div>
      <button data-testid="sync-health-refresh" onClick={onRefresh} className="ml-auto flex items-center gap-1 text-xs text-slate-400 hover:text-white">
        <RefreshCw className="h-3.5 w-3.5" /> Refresh
      </button>
    </div>
  );
}

function genRandomWalk(n = 1200) {
  const rows = []; let ts = Date.now() - n * 5000; let price = 100;
  for (let i = 0; i < n; i++) {
    ts += 5000;
    const o = price;
    const c = o + (Math.random() - 0.5) * 0.16;
    const hi = Math.max(o, c) + Math.random() * 0.06;
    const lo = Math.min(o, c) - Math.random() * 0.06;
    price = c;
    rows.push({ ts, open: +o.toFixed(5), high: +hi.toFixed(5), low: +lo.toFixed(5), close: +c.toFixed(5) });
  }
  return rows;
}

function CandleSpark({ candles, barIndex, direction }) {
  if (!candles?.length || barIndex == null) return null;
  const from = Math.max(0, barIndex - 44);
  const to = Math.min(candles.length, barIndex + 6);
  const win = candles.slice(from, to);
  const hi = Math.max(...win.map((c) => c.high));
  const lo = Math.min(...win.map((c) => c.low));
  const range = Math.max(1e-9, hi - lo);
  const H = 90, cw = 7, pad = 2;
  const W = win.length * cw;
  const y = (v) => H - ((v - lo) / range) * (H - 2 * pad) - pad;
  return (
    <svg data-testid="replay-sparkline" width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="mt-3 rounded bg-[#080808]">
      {win.map((c, i) => {
        const isTrigger = from + i === barIndex;
        const up = c.close >= c.open;
        const color = isTrigger ? "#2F8CFF" : up ? "#22C55E" : "#C62828";
        const x = i * cw + cw / 2;
        const bodyTop = y(Math.max(c.open, c.close));
        const bodyH = Math.max(1, Math.abs(y(c.open) - y(c.close)));
        return (
          <g key={i} opacity={isTrigger ? 1 : 0.85}>
            <line x1={x} x2={x} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth={isTrigger ? 1.4 : 0.8} />
            <rect x={i * cw + 1} y={bodyTop} width={cw - 2} height={bodyH} fill={color} />
            {isTrigger && <rect x={i * cw} y={0} width={cw} height={H} fill={color} opacity={0.12} />}
          </g>
        );
      })}
    </svg>
  );
}

function parseCandles(text) {
  const t = (text || "").trim();
  if (!t) return [];
  if (t[0] === "[" || t[0] === "{") {
    const a = JSON.parse(t);
    const arr = Array.isArray(a) ? a : a.candles || [];
    return arr.map((r, i) => ({ ts: +(r.ts ?? r.time ?? i * 5000), open: +r.open, high: +r.high, low: +r.low, close: +r.close }));
  }
  const lines = t.split(/\r?\n/).filter((l) => l.trim());
  const header = lines[0].toLowerCase().split(",").map((s) => s.trim());
  const hasHeader = header.includes("close");
  const idx = (k) => header.indexOf(k);
  const rows = [];
  for (let i = hasHeader ? 1 : 0; i < lines.length; i++) {
    const p = lines[i].split(",").map((s) => s.trim());
    if (hasHeader) rows.push({ ts: +(p[idx("ts")] || i * 5000), open: +p[idx("open")], high: +p[idx("high")], low: +p[idx("low")], close: +p[idx("close")] });
    else { const [ts, open, high, low, close] = p.map(Number); rows.push({ ts: ts || i * 5000, open, high, low, close }); }
  }
  return rows;
}

function drawShareCard({ candles, barIndex, sig, version }) {
  const W = 1200, Hc = 630;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = Hc;
  const g = cv.getContext("2d");
  // background
  g.fillStyle = "#0B0B0B"; g.fillRect(0, 0, W, Hc);
  g.strokeStyle = "#2F8CFF"; g.lineWidth = 3; g.strokeRect(14, 14, W - 28, Hc - 28);
  // wordmark
  g.fillStyle = "#2F8CFF"; g.font = "bold 54px Georgia, serif";
  g.fillText("KAOS TRADING", 60, 90);
  g.fillStyle = "#8a8a8a"; g.font = "600 20px Georgia, serif";
  g.fillText("TRADE WITH KAOS", 62, 122);
  // engine + direction
  g.fillStyle = "#ffffff"; g.font = "bold 84px Georgia, serif";
  g.fillText(sig.engine, 60, 240);
  const dirColor = sig.direction === "BUY" ? "#22C55E" : "#C62828";
  g.fillStyle = dirColor; g.font = "bold 60px Georgia, serif";
  g.fillText(sig.direction, 60, 315);
  g.fillStyle = "#cfcfcf"; g.font = "600 28px monospace";
  g.fillText(`expiry ${sig.expiration}   ·   confidence ${sig.confidence}   ·   v${version}`, 62, 360);
  // candlesticks
  const from = Math.max(0, barIndex - 44), to = Math.min(candles.length, barIndex + 6);
  const win = candles.slice(from, to);
  if (win.length) {
    const x0 = 60, y0 = 400, cw = (W - 120) / win.length, cH = 180;
    const hi = Math.max(...win.map((c) => c.high)), lo = Math.min(...win.map((c) => c.low));
    const rng = Math.max(1e-9, hi - lo);
    const yy = (v) => y0 + cH - ((v - lo) / rng) * cH;
    win.forEach((c, i) => {
      const trigger = from + i === barIndex;
      const up = c.close >= c.open;
      const col = trigger ? "#2F8CFF" : up ? "#22C55E" : "#C62828";
      const cx = x0 + i * cw + cw / 2;
      if (trigger) { g.fillStyle = "rgba(212,175,55,0.15)"; g.fillRect(x0 + i * cw, y0, cw, cH); }
      g.strokeStyle = col; g.lineWidth = trigger ? 2.4 : 1.4;
      g.beginPath(); g.moveTo(cx, yy(c.high)); g.lineTo(cx, yy(c.low)); g.stroke();
      g.fillStyle = col;
      const bt = yy(Math.max(c.open, c.close)), bh = Math.max(2, Math.abs(yy(c.open) - yy(c.close)));
      g.fillRect(x0 + i * cw + 2, bt, Math.max(2, cw - 4), bh);
    });
  }
  // footer
  g.fillStyle = "#6b6b6b"; g.font = "500 18px monospace";
  g.fillText("Signal preview · deterministic KAOS engine · not financial advice", 60, Hc - 40);
  return cv.toDataURL("image/png");
}

function StrategyReplay() {
  const [res, setRes] = useState(null);
  const [candles, setCandles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const scan = async (c) => {
    if (c.length < 40) { toast.error("Provide at least ~40 candle rows."); return; }
    setBusy(true); setRes(null); setCandles(c);
    try {
      const r = await api.post("/api/trading/strategy-preview", { candles: c, asset: "EURUSD" });
      setRes(r.data);
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };
  const run = () => scan(genRandomWalk(1200));
  const runPasted = () => {
    let c;
    try { c = parseCandles(pasteText).filter((x) => [x.open, x.high, x.low, x.close].every(Number.isFinite)); }
    catch (e) { toast.error("Could not parse candles. Use JSON array or CSV with open,high,low,close."); return; }
    scan(c);
  };
  const sig = res?.signal;
  return (
    <div className="card-surface mb-6 p-5" data-testid="strategy-replay">
      <div className="flex flex-wrap items-center gap-3">
        <Zap className="h-5 w-5 text-[#2F8CFF]" />
        <h3 className="font-heading font-semibold">Strategy Replay</h3>
        <span className="font-mono text-xs text-slate-500">Runs the real server-side KAOS engine — no live trade.</span>
        <div className="ml-auto flex items-center gap-2">
          <button data-testid="strategy-replay-paste-toggle" onClick={() => setShowPaste((v) => !v)} className="text-xs text-slate-400 hover:text-white">{showPaste ? "Hide paste" : "Paste candles"}</button>
          <Button data-testid="strategy-replay-run" onClick={run} disabled={busy} className="bg-[#22C55E] text-black">
            {busy ? "Scanning…" : "Run on demo market"}
          </Button>
        </div>
      </div>
      {showPaste && (
        <div className="mt-3">
          <Textarea data-testid="strategy-replay-paste-input" value={pasteText} onChange={(e) => setPasteText(e.target.value)}
            placeholder='Paste candles: JSON [{"ts","open","high","low","close"}, …] or CSV with header open,high,low,close'
            className="min-h-[90px] bg-[#080808] border-[#3A3A3A] font-mono text-xs" />
          <div className="mt-2 flex items-center gap-3">
            <Button data-testid="strategy-replay-run-pasted" onClick={runPasted} disabled={busy} size="sm" className="bg-[#2F8CFF] text-black">Run on pasted candles</Button>
            <span className="font-mono text-[10px] text-slate-500">Your data is analyzed live and never stored.</span>
          </div>
        </div>
      )}
      {res && (
        <div className="mt-4" data-testid="strategy-replay-result">
          {res.decision === "TRADE" && sig ? (
            <div className="rounded-md border border-[#2F8CFF]/30 bg-[#2F8CFF]/5 p-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <span className="font-heading text-lg font-bold text-[#2F8CFF]">{sig.engine}</span>
                <span className={`font-mono text-sm font-bold ${sig.direction === "BUY" ? "text-[#22C55E]" : "text-[#C62828]"}`}>{sig.direction}</span>
                <span className="font-mono text-xs text-slate-400">expiry {sig.expiration}</span>
                <span className="font-mono text-xs text-slate-400">confidence {sig.confidence}</span>
                <span className="ml-auto font-mono text-[10px] uppercase text-slate-500">bar {res.barIndex} / {res.bars} · v{res.strategyVersion} · LIVE</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">{sig.reason}</p>
              {sig.overlap && <p className="mt-1 font-mono text-[10px] text-slate-500">overlap: {sig.overlap.join(", ")}</p>}
              <CandleSpark candles={candles} barIndex={res.barIndex} direction={sig.direction} />
              <div className="mt-2 flex items-center justify-between">
                <p className="font-mono text-[10px] text-slate-500">Gold bar = engine trigger · window around the confirmed setup</p>
                <div className="flex items-center gap-2">
                  <Button data-testid="strategy-replay-link" size="sm" variant="outline" className="border-[#2E2E2E] bg-transparent text-slate-300 hover:bg-[#111]"
                    onClick={async () => {
                      try {
                        const from = Math.max(0, res.barIndex - 44), to = Math.min(candles.length, res.barIndex + 6);
                        const win = candles.slice(from, to);
                        const r = await api.post("/api/trading/share", { engine: sig.engine, direction: sig.direction, expiration: sig.expiration, confidence: sig.confidence, reason: sig.reason, strategyVersion: res.strategyVersion, asset: "EURUSD", candles: win, triggerPos: res.barIndex - from });
                        const url = window.location.origin + (r.data.ogPath || r.data.path);
                        await navigator.clipboard.writeText(url);
                        toast.success("Share link copied");
                      } catch (e) { toast.error("Could not create share link"); }
                    }}>
                    <LinkIcon className="mr-1 h-3.5 w-3.5" /> Copy share link
                  </Button>
                  <Button data-testid="strategy-replay-share" size="sm" variant="outline" className="border-[#2F8CFF]/40 bg-transparent text-[#2F8CFF] hover:bg-[#2F8CFF]/10"
                    onClick={() => {
                      try {
                        const url = drawShareCard({ candles, barIndex: res.barIndex, sig, version: res.strategyVersion });
                        const a = document.createElement("a"); a.href = url; a.download = `kaos-${sig.engine.toLowerCase()}-${sig.direction.toLowerCase()}.png`; a.click();
                        toast.success("Signal card downloaded");
                      } catch (e) { toast.error("Could not render share card"); }
                    }}>
                    <Share2 className="mr-1 h-3.5 w-3.5" /> Share this setup
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-md border border-[#2E2E2E] bg-[#0c0c0c] p-4 text-sm text-slate-400" data-testid="strategy-replay-notrade">
              No confirmed Reversal / Runner / Breakout setup in the last {res.scanned} windows (or an opposite-direction conflict blocked entry). Run again for a fresh market.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EquitySpark({ eq }) {
  if (!eq?.length) return null;
  const W = 600, H = 60, n = eq.length;
  const min = Math.min(0, ...eq), max = Math.max(0, ...eq);
  const rng = Math.max(1, max - min);
  const pts = eq.map((v, i) => `${(i / Math.max(1, n - 1)) * W},${H - ((v - min) / rng) * H}`).join(" ");
  const up = eq[eq.length - 1] >= 0;
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="mt-3 rounded bg-[#080808]">
      <polyline points={pts} fill="none" stroke={up ? "#22C55E" : "#C62828"} strokeWidth="1.5" />
    </svg>
  );
}

function BacktestExplorer() {
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const run = async (candles) => {
    if (candles.length < 60) { toast.error("Provide at least ~60 candle rows."); return; }
    setBusy(true); setRes(null);
    try { const r = await api.post("/api/trading/backtest", { candles, asset: "EURUSD" }); setRes(r.data); }
    catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };
  const engines = ["REVERSAL", "RUNNER", "BREAKOUT"];
  return (
    <div className="card-surface mb-6 p-5" data-testid="backtest-explorer">
      <div className="flex flex-wrap items-center gap-3">
        <LineChart className="h-5 w-5 text-[#2F8CFF]" />
        <h3 className="font-heading font-semibold">Backtest Explorer</h3>
        <span className="font-mono text-xs text-slate-500">real engine win-rate per strategy over market history</span>
        <div className="ml-auto flex items-center gap-2">
          <button data-testid="backtest-paste-toggle" onClick={() => setShowPaste((v) => !v)} className="text-xs text-slate-400 hover:text-white">{showPaste ? "Hide paste" : "Paste candles"}</button>
          <Button data-testid="backtest-run" onClick={() => run(genRandomWalk(1500))} disabled={busy} className="bg-[#22C55E] text-black">{busy ? "Running…" : "Run on demo history"}</Button>
        </div>
      </div>
      {showPaste && (
        <div className="mt-3">
          <Textarea data-testid="backtest-paste-input" value={pasteText} onChange={(e) => setPasteText(e.target.value)}
            placeholder='Paste candles: JSON array or CSV with open,high,low,close' className="min-h-[80px] bg-[#080808] border-[#3A3A3A] font-mono text-xs" />
          <Button data-testid="backtest-run-pasted" onClick={() => { try { run(parseCandles(pasteText).filter((x) => [x.open, x.high, x.low, x.close].every(Number.isFinite))); } catch (e) { toast.error("Could not parse candles."); } }} disabled={busy} size="sm" className="mt-2 bg-[#2F8CFF] text-black">Run on pasted candles</Button>
        </div>
      )}
      {res && (
        <div className="mt-4" data-testid="backtest-result">
          <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-1">
            <span className="font-mono text-sm text-slate-300">Overall</span>
            <span className="font-mono text-2xl font-bold text-[#2F8CFF]" data-testid="backtest-overall-winrate">{res.overall.winRate}%</span>
            <span className="font-mono text-xs text-slate-400">{res.overall.trades} trades · {res.overall.wins}W / {res.overall.losses}L / {res.overall.ties}T</span>
            <span className="ml-auto font-mono text-[10px] uppercase text-slate-500">{res.bars} bars · v{res.strategyVersion} · LIVE</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {engines.map((e) => {
              const d = res.byEngine[e] || { trades: 0, wins: 0, losses: 0, ties: 0, winRate: 0 };
              return (
                <div key={e} className="rounded-md border border-[#2E2E2E] bg-[#0c0c0c] p-3" data-testid={`backtest-engine-${e}`}>
                  <div className="label-mono">{e}</div>
                  <div className="mt-1 font-mono text-xl font-bold text-[#2F8CFF]">{d.winRate}%</div>
                  <div className="mt-1 font-mono text-[10px] text-slate-500">{d.trades} trades · {d.wins}W/{d.losses}L/{d.ties}T</div>
                </div>
              );
            })}
          </div>
          <EquitySpark eq={res.equity} />
          <p className="mt-1 text-center font-mono text-[10px] text-slate-500">Equity curve (wins +1 / losses −1) · non-overlapping trades · not financial advice</p>
        </div>
      )}
    </div>
  );
}

export default function Trading() {
  const [d, setD] = useState(null);
  const [sync, setSync] = useState(null);
  const [syncExpired, setSyncExpired] = useState(false);
  const load = () => api.get("/api/trading/overview").then((r) => setD(r.data)).catch(() => {});
  const loadSync = () => api.get("/api/trading/sync-status")
    .then((r) => { setSync(r.data); setSyncExpired(false); })
    .catch((e) => { if (e?.response?.status === 401) setSyncExpired(true); });
  useEffect(() => { load(); loadSync(); }, []);
  useEffect(() => { const id = setInterval(loadSync, 30000); return () => clearInterval(id); }, []);

  const setMode = async (mode) => {
    try { await api.post("/api/trading/mode", { mode }); toast.success(`Trading mode: ${MODE_META[mode].label}`); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  if (!d) return <p className="text-slate-500">Loading…</p>;
  const ent = d.entitlements;
  const s = d.summary;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-heading text-2xl font-bold tracking-wide">Trading</h1>
        <StatusBadge value={ent.botAccess ? "ACTIVE" : "EXPIRED"} testid="trading-bot-access" />
      </div>

      <FourChartTerminal entitlements={ent} />
      <div className="mb-6"><TrendPauseBacktest /></div>
      <div className="mb-6 rounded-lg border border-[#2F8CFF]/20 bg-[#2F8CFF]/5 p-3 text-xs text-[#2F8CFF]">
        The real KAOS Strategy (Berserker · Reversal/Runner/Breakout) runs server-side and returns live decisions when the extension streams market candles. KAOS AI serves live inference once a trained model is deployed. Broker execution happens only inside the extension — no live trades occur on this page.
      </div>

      <SyncHealth sync={sync} expired={syncExpired} onRefresh={loadSync} />

      <StrategyReplay />

      <BacktestExplorer />

      {/* Mode selector */}
      <div className="mb-6">
        <div className="label-mono mb-2">Trading Mode</div>
        <div className="grid gap-4 md:grid-cols-3">
          {["STRATEGY", "AI", "STRATEGY_AI"].map((m) => {
            const M = MODE_META[m]; const allowed = (ent.modes || []).includes(m); const active = d.mode === m;
            return (
              <button key={m} data-testid={`trading-mode-${m}`} disabled={!allowed} onClick={() => setMode(m)}
                className={`card-surface p-5 text-left transition-all ${active ? "border-[#2F8CFF] ring-1 ring-[#2F8CFF]/40" : ""} ${!allowed ? "opacity-50 cursor-not-allowed" : "hover:border-[#2F8CFF]/60"}`}>
                <div className="flex items-center justify-between">
                  <M.icon className={`h-6 w-6 ${active ? "text-[#2F8CFF]" : "text-slate-400"}`} />
                  {!allowed && <Lock className="h-4 w-4 text-slate-500" />}
                  {active && <span className="font-mono text-[10px] uppercase text-[#2F8CFF]">Active</span>}
                </div>
                <div className="mt-3 font-heading font-semibold">{M.label}</div>
                <p className="mt-1 text-sm text-slate-400">{M.desc}</p>
                {!allowed && <p className="mt-2 text-xs text-slate-500">Upgrade to unlock</p>}
              </button>
            );
          })}
        </div>
      </div>

      {/* KAOS Strategy engines */}
      <div className="card-surface mb-6 p-5">
        <div className="flex items-center gap-2"><Cpu className="h-5 w-5 text-[#2F8CFF]" />
          <h3 className="font-heading font-semibold">{d.officialStrategy.name} <span className="font-mono text-xs text-slate-500">v{d.officialStrategy.version} · {d.officialStrategy.structureComponent}</span></h3>
          <span className="ml-auto inline-flex items-center gap-1 rounded bg-[#2F8CFF]/10 border border-[#2F8CFF]/30 px-2 py-0.5 font-mono text-[10px] uppercase text-[#2F8CFF]"><Lock className="h-3 w-3" />Official · Locked</span>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {d.officialStrategy.engines.map((e) => (
            <div key={e.key} className="rounded-md border border-[#2E2E2E] bg-[#0c0c0c] p-4">
              <div className="flex items-center justify-between"><span className="font-heading font-semibold text-white">{e.label}</span>
                <span className="font-mono text-xs text-[#2F8CFF]">{e.expiration}</span></div>
              <p className="mt-2 text-xs text-slate-400">{e.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {[["Signals", s.signals], ["Attempts", s.orderAttempts], ["Confirmed", s.brokerConfirmed],
          ["Failed", s.failed], ["Win Rate", s.winRate != null ? s.winRate + "%" : "—"], ["Net P/L", s.netPnl]].map(([l, v]) => (
          <div key={l} className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-xl font-bold text-[#2F8CFF]">{v}</div></div>
        ))}
      </div>

      {/* Recent trades */}
      <div className="card-surface p-0 overflow-x-auto">
        <div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Recent Executions</h3>
          <p className="text-xs text-slate-500">A signal is not a trade — only broker-confirmed orders become real trades.</p></div>
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Asset</TableHead><TableHead>Dir</TableHead><TableHead>Engine</TableHead><TableHead>Mode</TableHead><TableHead>State</TableHead><TableHead>Result</TableHead><TableHead>P/L</TableHead></TableRow></TableHeader>
          <TableBody>
            {d.recentTrades.length === 0 && <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-6">No executions yet.</TableCell></TableRow>}
            {d.recentTrades.map((t) => (
              <TableRow key={t.id} className="border-[#2E2E2E]" data-testid={`trade-row-${t.id}`}>
                <TableCell className="font-mono text-sm">{t.asset}</TableCell>
                <TableCell className={t.direction === "BUY" ? "text-[#2F8CFF]" : "text-[#C62828]"}>{t.direction}</TableCell>
                <TableCell className="font-mono text-xs">{t.engine || "—"}</TableCell>
                <TableCell className="font-mono text-xs">{t.tradingMode}</TableCell>
                <TableCell className={`font-mono text-xs ${STATE_COLOR[t.state] || ""}`}>{t.state}{t.simulated && " ·SIM"}</TableCell>
                <TableCell className={t.result === "WIN" ? "text-[#2F8CFF]" : t.result === "LOSS" ? "text-[#C62828]" : "text-slate-400"}>{t.result || (t.failureCode ? t.failureCode : "—")}</TableCell>
                <TableCell className="font-mono text-xs">{t.pnl != null ? t.pnl : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
