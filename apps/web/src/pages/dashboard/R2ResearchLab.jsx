import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";

const API = "/api/v1/owner/candles/r2-lab";
const box = "rounded-lg border border-[#34302A] bg-[#11100E] p-4";
const input = "w-full rounded border border-[#4B4334] bg-[#080808] px-3 py-2 text-sm text-white";
const button = "rounded bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-40";
const ratio = n => n == null ? "—" : (n * 100).toFixed(1) + "%";
const win = n => n == null ? "—" : n + "%";

export default function R2ResearchLab() {
  const [markets, setMarkets] = useState([]);
  const [market, setMarket] = useState("BTC-USD");
  const [limit, setLimit] = useState(300);
  const [expiry, setExpiry] = useState(4);
  const [lookback, setLookback] = useState(12);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [models, setModels] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [patternStatus, setPatternStatus] = useState([]);
  const [observations, setObservations] = useState([]);
  const [patternCatalog, setPatternCatalog] = useState(null);
  const [shadow, setShadow] = useState({predictions:[],summary:{}});
  const [accessDenied, setAccessDenied] = useState(false);
  const [botSignals, setBotSignals] = useState([]);
  const [botSignalError, setBotSignalError] = useState("");
  const loadBotSignals = async (symbol = market) => {
    try {
      const {data} = await api.get(API + "/bot-signal-preview", {params:{symbol,limit:10}});
      setBotSignals(data.signals || []);
      setBotSignalError("");
    } catch(e) { setBotSignalError(errMsg(e) || "Research signal preview unavailable"); }
  };

  const selected = markets.find(m => m.symbol === market);
  const load = async () => {
    try {
      const [{data: m}, {data: b}, {data: a}] = await Promise.all([
        api.get(API + "/markets"), api.get(API + "/backtests"), api.get(API + "/models")
      ]);
      setMarkets(m.markets || []);
      setHistory(b.runs || []);
      setModels(a.models || []);
      setAccessDenied(false);
    } catch (e) {
      setAccessDenied(e?.response?.status === 403);
      setError(errMsg(e) || "Could not load R2 research");
    }
  };
  const loadPatterns = async (symbol = market) => {
    try {
      const [{data: states},{data: events},{data: cats}] = await Promise.all([
        api.get(API + "/patterns/status"),
        api.get(API + "/patterns/observations", {params:{symbol,limit:50}}),
        api.get(API + "/patterns/catalog")
      ]);
      setPatternStatus(states.markets || []);
      setObservations(events.observations || []);
      setPatternCatalog(cats);
    } catch(e) { setError(errMsg(e) || "Pattern observations unavailable"); }
  };
  const loadShadow = async (symbol = market) => {
    try {
      const {data} = await api.get(API + "/shadow", {params:{symbol,limit:60}});
      setShadow(data);
    } catch(e) { setError(errMsg(e) || "Shadow forecasts unavailable"); }
  };
  useEffect(() => { load(); loadPatterns("BTC-USD"); loadShadow("BTC-USD"); loadBotSignals("BTC-USD"); }, []);
  const switchMarket = value => {setMarket(value);setObservations([]);setShadow({predictions:[],summary:{}});loadPatterns(value);loadShadow(value);loadBotSignals(value);};
  const runBacktest = async e => {
    e.preventDefault();
    if (!selected) return;
    setError(""); setMessage(""); setBusy("backtest");
    try {
      const {data} = await api.post(API + "/backtest", {
        symbol: market, asset_class: selected.asset_class,
        limit: Number(limit), expiry_bars: Number(expiry), lookback: Number(lookback)
      });
      setResult(data);
      setMessage("Backtest saved to private KAOS research history.");
      const {data: recent} = await api.get(API + "/backtests");
      setHistory(recent.runs || []);
    } catch (e) { setError(errMsg(e) || "Backtest failed"); }
    finally { setBusy(""); }
  };
  const train = async () => {
    if (!selected) return;
    setError(""); setMessage(""); setBusy("training");
    try {
      const {data} = await api.post(API + "/train", {
        symbol: market, asset_class: selected.asset_class,
        limit: Math.max(300, Number(limit)), horizon_bars: Number(expiry)
      });
      setMessage(data.ok
        ? "New research-only AI candidate saved. Its holdout validation is displayed below."
        : (data.required || "Not enough continuous, labeled historical samples to train."));
      const {data: latest} = await api.get(API + "/models");
      setModels(latest.models || []);
    } catch (e) { setError(errMsg(e) || "AI training failed"); }
    finally { setBusy(""); }
  };
  const promote = async modelId => {
    if (!window.confirm("Promote this validated model to research-active status ONLY? This does not enable live AI trading.")) return;
    setError(""); setMessage(""); setBusy("promotion");
    try {
      await api.post(API + "/promote", {model_id: modelId});
      setMessage("Model promoted inside research registry only. Live AI trading remains disabled.");
      const {data} = await api.get(API + "/models");
      setModels(data.models || []);
    } catch (e) { setError(errMsg(e) || "Research promotion blocked"); }
    finally { setBusy(""); }
  };

  return <section className="space-y-5 text-white" data-testid="r2-research-lab">
    <div>
      <h1 className="font-heading text-2xl font-bold text-[#D4AF37]">KAOS Backtesting & AI Research Lab</h1>
      <p className="mt-2 text-sm text-slate-400">Private Cloudflare R2 candles · chronological AI evaluation · no broker orders</p>
    </div>
    {accessDenied ? <div className={box} role="alert">This private archive research lab is available only to the configured KAOS owner. Your ordinary member backtests remain separate.</div> : <>
      <form onSubmit={runBacktest} className={box + " space-y-4"}>
        <h2 className="font-semibold text-[#D4AF37]">Historical R2 Backtesting</h2>
        <div className="grid gap-3 sm:grid-cols-4">
          <label className="text-xs text-slate-300">Market
            <select value={market} onChange={e => switchMarket(e.target.value)} className={"mt-1 " + input}>
              {markets.map(m => <option key={m.symbol} value={m.symbol}>{m.symbol} · {m.asset_class}</option>)}
            </select>
          </label>
          <label className="text-xs text-slate-300">Archived candles (100–5000)
            <input aria-label="Candle limit" className={"mt-1 " + input} type="number" min="100" max="5000" value={limit} onChange={e => setLimit(e.target.value)} />
          </label>
          <label className="text-xs text-slate-300">Exit horizon (minutes)
            <select aria-label="Exit horizon" value={expiry} onChange={e => setExpiry(e.target.value)} className={"mt-1 " + input}>
              {[1,2,3,4,5,10,15,30].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="text-xs text-slate-300">Structure lookback (bars)
            <input className={"mt-1 " + input} type="number" min="5" max="100" value={lookback} onChange={e => setLookback(e.target.value)} />
          </label>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={!!busy || !selected} className={button}>{busy === "backtest" ? "Backtesting…" : "Run R2 Backtest"}</button>
          <button type="button" disabled={!!busy || !selected || Number(limit) < 300} onClick={train}
            className="rounded border border-[#D4AF37] px-4 py-2 text-sm font-semibold text-[#D4AF37] disabled:opacity-40">
            {busy === "training" ? "Training…" : "Train AI Research Candidate"}
          </button>
        </div>
        <p className="text-xs text-amber-300">One-minute candles only. Results are idealized OHLC directional tests without fees, spread, slippage, payout or live-fill proof. AI training uses a separate deterministic logistic research model, not the live KAOS AI engine.</p>
      </form>

      {error && <p role="alert" className="rounded border border-red-700 p-3 text-sm text-red-300">{error}</p>}
      {message && <p role="status" className="rounded border border-[#74612D] p-3 text-sm text-[#D4AF37]">{message}</p>}

      {result && <div className={box + " space-y-3"} aria-live="polite">
        <h2 className="font-semibold">Latest backtest · {result.symbol}</h2>
        <p className="text-xs text-slate-400">{result.status} · {result.history?.eligible_bars ?? 0} eligible candles · {result.history?.skipped_bars ?? 0} skipped · {result.history?.gap_count ?? 0} gaps</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[["Trades",result.summary?.trades],["Wins",result.summary?.wins],
            ["Losses",result.summary?.losses],["Ties",result.summary?.ties],
            ["Directional WR",win(result.summary?.win_rate_ex_ties)],
            ["Trades/hour",result.summary?.trades_per_hour ?? "—"],
            ["Usable hours",result.summary?.data_hours ?? "—"]
          ].map(([label,value]) => <div key={label} className="rounded bg-[#1C1A16] p-3">
            <p className="text-xs text-slate-400">{label}</p><p className="text-lg font-semibold">{value ?? "—"}</p>
          </div>)}
        </div>
        <div className="max-h-72 overflow-auto">
          <table className="w-full min-w-[650px] text-left text-xs">
            <thead><tr className="border-b border-[#444]">{["Entry UTC","Setup","Direction","Entry","Exit","Outcome"].map(h=><th className="p-2" key={h}>{h}</th>)}</tr></thead>
            <tbody>{(result.trades || []).map((t,i)=><tr key={i} className="border-b border-[#292929]">
              <td className="p-2">{new Date(t.entry_ts).toISOString()}</td>
              <td className="p-2">{t.setup}</td><td className="p-2">{t.direction}</td>
              <td className="p-2">{t.entry_price}</td><td className="p-2">{t.exit_price}</td>
              <td className="p-2">{t.outcome}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </div>}

      <div className={box}>
        <h2 className="mb-3 font-semibold text-[#D4AF37]">Recent R2 backtests</h2>
        <div className="max-h-56 overflow-auto text-sm">
          {!history.length && <p className="text-slate-500">No website-generated R2 backtests yet. Existing terminal JSON reports are stored separately.</p>}
          {history.map(r => <div key={r.id} className="flex flex-wrap justify-between gap-2 border-b border-[#262626] py-2">
            <span>{r.symbol} · {r.expiry_bars}m · {r.status}</span>
            <span className="font-mono">{r.summary?.trades ?? 0} trades · {win(r.summary?.win_rate_ex_ties)} WR · {r.created_at}</span>
          </div>)}
        </div>
      </div>

      <div className={box + " space-y-3"} data-testid="kaos-ai-bot-signal-preview">
        <div className="flex flex-wrap justify-between gap-3">
          <div>
            <h2 className="font-semibold text-[#D4AF37]">KAOS AI → Trading Bot Signal Preview</h2>
            <p className="text-xs text-slate-400">Versioned research observations · not order instructions · no execution authority</p>
          </div>
          <button type="button" onClick={() => loadBotSignals(market)}
            className="rounded border border-[#D4AF37] px-3 py-2 text-xs text-[#D4AF37]">Refresh signals</button>
        </div>
        {botSignalError && <p className="text-sm text-amber-300">{botSignalError}</p>}
        {!botSignals.length && <p className="text-sm text-slate-400">No valid model-backed research signals available for {market}.</p>}
        <div className="max-h-64 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead><tr>{["Market","AI direction","P(up)","Horizon","Model","Block reasons"].map(s =>
              <th key={s} className="border-b border-[#34302A] p-2">{s}</th>)}</tr></thead>
            <tbody>{botSignals.map(s => <tr key={s.id} className="border-b border-[#292929]">
              <td className="p-2">{s.symbol}</td><td className="p-2">{s.bias}</td>
              <td className="p-2">{ratio(s.prob_up)}</td>
              <td className="p-2">{s.horizon_seconds}s</td>
              <td className="p-2">{s.model_validation_status}</td>
              <td className="p-2">{s.block_reasons.join(", ")}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p className="text-xs text-amber-300">AI research signals are not executable orders. The trading bot must independently verify entitlement, current broker quotes, strategy authority, risk limits and emergency stop before any future paper/live integration.</p>
      </div>

      <div className={box + " space-y-3"} data-testid="kaos-ai-shadow-forecasts">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-[#D4AF37]">KAOS AI Shadow Predictions</h2>
            <p className="text-xs text-slate-400">Trained-model forecasts on completed R2 candles · independently verified later · no orders</p>
          </div>
          <button type="button" onClick={() => loadShadow(market)} className="rounded border border-[#D4AF37] px-3 py-2 text-xs text-[#D4AF37]">Refresh forecasts</button>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Saved forecasts",shadow.summary?.shown ?? 0],
            ["Verified outcomes",shadow.summary?.settled ?? 0],
            ["HOLD decisions",shadow.summary?.hold ?? 0],
            ["Directional accuracy",ratio(shadow.summary?.directional_accuracy)]
          ].map(([label,value]) => <div key={label} className="rounded bg-[#1C1A16] p-3">
            <p className="text-xs text-slate-400">{label}</p><p className="font-semibold">{value}</p>
          </div>)}
        </div>
        <p className="text-xs text-amber-300">Shadow signals may come from unvalidated candidate models. An accuracy value here is not a live trading win rate: predictions overlap and exclude spread, costs, fills and payout. Automatic research schedules require separate cPanel activation.</p>
        {!shadow.predictions?.length && <p className="text-sm text-slate-500">No shadow predictions for {market} yet. Run training and activate the research prediction schedule after deployment.</p>}
        <div className="max-h-64 overflow-auto">
          <table className="w-full min-w-[730px] text-left text-xs">
            <thead><tr className="border-b border-[#444]">{["Observation UTC","Direction","P(up)","Horizon","Validation","Actual outcome","Result"].map(h=><th key={h} className="p-2">{h}</th>)}</tr></thead>
            <tbody>{(shadow.predictions || []).map(p => <tr key={p.id} className="border-b border-[#282828]">
              <td className="p-2">{new Date(p.observed_ts).toISOString()}</td>
              <td className="p-2">{p.direction}</td>
              <td className="p-2">{ratio(p.prob_up)}</td>
              <td className="p-2">{p.horizon_bars} bars</td>
              <td className="p-2">{p.validation_status}</td>
              <td className="p-2">{p.outcome_status === "settled" ? p.outcome_direction : "Pending"}</td>
              <td className="p-2">{p.correct === true ? "Matched" : p.correct === false ? "Missed" : "—"}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </div>

      <div className={box + " space-y-3"} data-testid="kaos-pattern-observer">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-[#D4AF37]">KAOS Market Pattern Observer</h2>
            <p className="text-xs text-slate-400">Codex's completed-candle pattern library · runs without trades · research only</p>
          </div>
          <button type="button" onClick={() => loadPatterns(market)} className="rounded border border-[#D4AF37] px-3 py-2 text-xs text-[#D4AF37]">Refresh observations</button>
        </div>
        <p className="text-sm">{patternCatalog ? `${patternCatalog.implemented_count}/${patternCatalog.catalog_count} patterns implemented` : "Pattern catalog loading…"} · {patternStatus.length} markets with saved observer state</p>
        <p className="text-xs text-slate-400">The private scheduled scanner must be activated separately in cPanel. Recording candle patterns is not the same as training a model on those features.</p>
        {!observations.length && <p className="text-sm text-slate-500">No pattern observations stored for {market} yet.</p>}
        <div className="max-h-64 overflow-x-auto">
          <table className="w-full min-w-[660px] text-left text-xs">
            <thead><tr className="border-b border-[#444]">{["Candle UTC","Pattern","Direction","1-bar outcome","4-bar outcome","10-bar outcome"].map(h=><th className="p-2" key={h}>{h}</th>)}</tr></thead>
            <tbody>{observations.map(e => <tr key={e.id} className="border-b border-[#282828]">
              <td className="p-2">{new Date(e.observed_ts).toISOString()}</td>
              <td className="p-2">{e.pattern}</td>
              <td className="p-2">{e.direction}</td>
              {[1,4,10].map(h => <td key={h} className="p-2">{e.outcomes?.[h]?.direction ?? "Pending"}</td>)}
            </tr>)}</tbody>
          </table>
        </div>
      </div>

      <div className={box + " space-y-4"}>
        <div>
          <h2 className="font-semibold text-[#D4AF37]">AI Research Training & Validation</h2>
          <p className="mt-1 text-xs text-slate-400">Completed candles only. Training, validation and untouched test periods are chronological, with label-overlap purging. Research promotion requires minimum held-out evidence and does not deploy the trading AI.</p>
        </div>
        {!models.length && <p className="text-sm text-slate-500">No R2 research models trained yet.</p>}
        {models.map(m => <div key={m.id} className="rounded border border-[#423A2E] p-4">
          <div className="flex flex-wrap justify-between gap-2">
            <strong>{m.symbol} · {m.strategy}</strong>
            <span className="text-sm text-[#D4AF37]">{m.status} · {m.validation_status}</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{m.samples} labeled samples · {m.train_samples} train / {m.validation_samples} validation / {m.test_samples} test</p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <div>Test accuracy: <strong>{ratio(m.test?.accuracy)}</strong></div>
            <div>Test signals: <strong>{m.test?.signals ?? "—"}</strong></div>
            <div>Signals/hour: <strong>{m.test?.trades_per_hour ?? "—"}</strong></div>
            <div>95% lower bound: <strong>{ratio(m.test?.wilson_lower_95)}</strong></div>
          </div>
          {(m.promotion_blockers || []).length > 0 && <p className="mt-3 text-xs text-amber-300">Not validated: {m.promotion_blockers.join("; ")}</p>}
          {m.validation_status === "validated_research_candidate" && m.status !== "research_active" &&
            <button type="button" disabled={!!busy} onClick={() => promote(m.id)} className={button + " mt-3"}>Promote to Research-Active Only</button>}
          {m.status === "research_active" && <p className="mt-2 text-sm text-[#D4AF37]">Research-active; no live execution authority.</p>}
        </div>)}
      </div>
    </>}
  </section>;
}
