import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import {
  ALERT_KINDS, CRYPTO_UNIVERSE, SIGNAL_CODES, buildAlertPayload, filterRows, formatNumber,
  formatPct, freshnessLabel, parseSymbols, signalTone, sortRows, sparkPath,
} from "../../lib/intel";
import {
  Activity, AlertTriangle, ArrowUpRight, Bell, BookmarkPlus, FlaskConical, LineChart,
  RefreshCw, Search, ShieldAlert, Trash2, Waves,
} from "lucide-react";

const TABS = [
  ["overview", "Overview", LineChart],
  ["crypto", "Crypto", Activity],
  ["stocks", "Stocks", Search],
  ["social", "Social", Waves],
  ["options", "Options", FlaskConical],
  ["watch", "Watchlists & Alerts", Bell],
];

const card = "rounded-xl border border-[#2E2E2E] bg-[#0F0F0F]";
const th = "px-3 py-2 text-left font-mono text-[10px] uppercase tracking-wider text-slate-500 whitespace-nowrap";
const td = "px-3 py-3 align-top text-sm text-slate-300 whitespace-nowrap";

function useRequest() {
  const [state, setState] = useState({ loading: false, error: "", status: 0, data: null });
  const run = useCallback(async (path, config) => {
    setState((prev) => ({ ...prev, loading: true, error: "" }));
    try {
      const response = await api.get(path, config);
      setState({ loading: false, error: "", status: response.status, data: response.data });
      return response.data;
    } catch (error) {
      setState({ loading: false, error: errMsg(error), status: error?.response?.status || 0, data: null });
      return null;
    }
  }, []);
  return [state, run];
}

function Chip({ children, tone = "neutral" }) {
  const tones = {
    neutral: "border-[#3A3A3A] bg-[#151515] text-slate-300",
    bull: "border-[#2F8CFF]/30 bg-[#2F8CFF]/10 text-[#2F8CFF]",
    bear: "border-[#C62828]/30 bg-[#C62828]/10 text-[#C62828]",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  };
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${tones[tone] || tones.neutral}`}>
      {children}
    </span>
  );
}

function Sparkline({ values }) {
  const points = sparkPath(values);
  if (!points) return <span className="font-mono text-xs text-slate-600">—</span>;
  return (
    <svg width="96" height="28" viewBox="0 0 96 28" aria-hidden="true" className="text-[#2F8CFF]">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function Signals({ signals = [] }) {
  if (!signals.length) return <span className="font-mono text-xs text-slate-600">none</span>;
  return (
    <div className="flex max-w-[280px] flex-wrap gap-1">
      {signals.map((signal) => (
        <span key={signal.code} title={signal.evidence}
          className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${signalTone(signal.direction)}`}>
          {signal.code}
        </span>
      ))}
    </div>
  );
}

function State({ state, label = "Loading…", isEmpty = false, empty = null, children }) {
  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-2 p-8 font-mono text-sm text-slate-400">
        <RefreshCw className="h-4 w-4 animate-spin" /> {label}
      </div>
    );
  }
  if (state.status === 403) {
    return (
      <div className="m-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-5">
        <p className="font-semibold text-amber-200">Market Intelligence scanners need Pro or Ultimate</p>
        <p className="mt-1 text-sm text-amber-100/80">{state.error}</p>
        <Link to="/dashboard/subscription">
          <Button className="mt-3 bg-[#22C55E] font-semibold text-black">See memberships</Button>
        </Link>
      </div>
    );
  }
  if (state.error) {
    return (
      <div role="alert" className="m-4 rounded-lg border border-[#C62828]/40 bg-[#C62828]/10 p-4 text-sm text-red-200">
        {state.error}
      </div>
    );
  }
  if (isEmpty && empty) return empty;
  return children;
}

function Attribution({ data }) {
  if (!data) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-[#2E2E2E] px-4 py-3 font-mono text-[11px] text-slate-500">
      {data.source && <span>Source: {data.source}{data.feed ? ` · ${data.feed.toUpperCase()}` : ""}</span>}
      {data.source_url && (
        <a className="text-[#2F8CFF] hover:underline" href={data.source_url} target="_blank" rel="noopener noreferrer">
          Provider documentation <ArrowUpRight className="inline h-3 w-3" />
        </a>
      )}
      {data.fetched_at && <span>Fetched {new Date(data.fetched_at).toLocaleString()}</span>}
      {data.coverage_note && <span className="basis-full text-slate-500">{data.coverage_note}</span>}
    </div>
  );
}

function ScanToolbar({ children, onRun, loading, label = "Run scan" }) {
  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-[#2E2E2E] p-4">
      {children}
      <Button onClick={onRun} disabled={loading} data-testid="intel-run-scan"
        className="bg-[#2F8CFF] font-semibold text-white hover:bg-[#1f78e0]">
        <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} /> {label}
      </Button>
    </div>
  );
}

function MetricFilters({ query, setQuery, signalsOnly, setSignalsOnly }) {
  return (
    <>
      <div>
        <Label className="label-mono" htmlFor="intel-filter">Filter</Label>
        <Input id="intel-filter" value={query} onChange={(event) => setQuery(event.target.value)}
          placeholder="Symbol" className="mt-1 w-36 border-[#3A3A3A] bg-[#080808]" />
      </div>
      <label className="flex items-center gap-2 pb-2 text-sm text-slate-400">
        <input type="checkbox" checked={signalsOnly} onChange={(event) => setSignalsOnly(event.target.checked)} />
        Signals only
      </label>
    </>
  );
}

function ScanTable({ rows, loading, error, status, emptyMessage, source }) {
  const state = { loading, error, status };
  return (
    <State state={state} label="Scanning completed candles…" isEmpty={rows.length === 0}
      empty={<p className="p-6 text-sm text-slate-400">{emptyMessage}</p>}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse">
          <thead>
            <tr className="border-b border-[#2E2E2E]">
              {["Symbol", "Last", "5-bar", "15-bar", "Vol ×20", "ATR%", "Structure", "Trend", "Signals", "Trend (30)", "Score", "As of"].map((label) => (
                <th key={label} className={th}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.symbol} data-testid={`scan-row-${row.symbol}`} className="border-b border-[#1c1c1c] hover:bg-[#141414]">
                <td className={`${td} font-semibold text-white`}>{row.symbol}</td>
                <td className={`${td} font-mono`}>{formatNumber(row.last_close, 6)}</td>
                <td className={`${td} font-mono ${Number(row.change_5_bars_pct) >= 0 ? "text-[#2F8CFF]" : "text-[#C62828]"}`}>
                  {formatPct(row.change_5_bars_pct)}
                </td>
                <td className={`${td} font-mono`}>{formatPct(row.change_15_bars_pct)}</td>
                <td className={`${td} font-mono`}>{row.volume_ratio_20 == null ? "—" : `${row.volume_ratio_20.toFixed(2)}x`}</td>
                <td className={`${td} font-mono`}>{row.atr_pct == null ? "—" : `${row.atr_pct.toFixed(2)}%`}</td>
                <td className={td}>
                  <Chip tone={row.structure === "breakout" ? "bull" : row.structure === "breakdown" ? "bear" : "neutral"}>
                    {row.structure.replace(/_/g, " ")}
                  </Chip>
                </td>
                <td className={td}>{row.trend.replace(/_/g, " ")}</td>
                <td className={td}><Signals signals={row.signals} /></td>
                <td className={td}><Sparkline values={row.sparkline} /></td>
                <td className={`${td} font-mono text-[#2F8CFF]`}>{row.attention_score}</td>
                <td className={`${td} font-mono text-xs text-slate-500`}>
                  {new Date(row.as_of).toLocaleTimeString()} · {freshnessLabel(row)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {source}
    </State>
  );
}

function QuickWatch({ onWatch }) {
  return (
    <button type="button" onClick={onWatch}
      className="inline-flex items-center gap-1 rounded border border-[#3A3A3A] px-2 py-1 font-mono text-[10px] text-slate-300 hover:border-[#2F8CFF] hover:text-[#2F8CFF]">
      <BookmarkPlus className="h-3 w-3" /> Watch
    </button>
  );
}

function Overview({ catalog, health, radar, onRefresh }) {
  const modules = catalog.data?.modules || [];
  const statusTone = (status) => {
    if (["live_public_feed", "provider_configured", "ingested_observations"].includes(status)) return "good";
    if (["provider_not_configured", "collector_not_configured"].includes(status)) return "warn";
    return "bear";
  };
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <State state={catalog} isEmpty={!modules.length}
          empty={null}>
          {modules.map((module) => (
            <div key={module.key} className={`${card} p-4`}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-heading font-semibold text-white">{module.name}</h3>
                <Chip tone={statusTone(module.data_status)}>{module.data_status.replace(/_/g, " ")}</Chip>
              </div>
              <p className="mt-2 text-xs text-slate-400">{module.coverage}</p>
              {module.required_env?.length > 0 && module.data_status === "provider_not_configured" && (
                <p className="mt-2 font-mono text-[11px] text-amber-300">Needs server keys: {module.required_env.join(", ")}</p>
              )}
            </div>
          ))}
        </State>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={card}>
          <div className="flex items-center justify-between border-b border-[#2E2E2E] p-4">
            <h2 className="font-heading font-semibold">Radar research candidates</h2>
            <Button onClick={onRefresh} size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white">
              <RefreshCw className="mr-1 h-3.5 w-3.5" /> Refresh
            </Button>
          </div>
          <State state={radar} isEmpty={!(radar.data?.results || []).length}
            empty={<p className="p-5 text-sm text-slate-400">No fused observations stored yet.</p>}>
            <div className="divide-y divide-[#1c1c1c]">
              {(radar.data?.results || []).slice(0, 6).map((row) => (
                <div key={`${row.asset}-${row.asset_class}`} className="flex items-start justify-between gap-3 p-4">
                  <div>
                    <p className="font-semibold text-white">{row.asset} <span className="font-mono text-xs text-slate-500">{row.asset_class}</span></p>
                    <p className="mt-1 text-xs text-slate-400">
                      {row.bias} · {row.status.replace(/_/g, " ")} · {row.confirming_directional_sources} confirming / {row.opposing_directional_sources} opposing
                    </p>
                  </div>
                  <span className="font-mono text-sm text-[#2F8CFF]">{row.score}</span>
                </div>
              ))}
            </div>
          </State>
          <div className="border-t border-[#2E2E2E] p-4">
            <Link to="/dashboard/opportunities" className="text-sm text-[#2F8CFF] hover:underline">
              Open the full Opportunity Radar →
            </Link>
          </div>
        </div>

        <div className={card}>
          <div className="border-b border-[#2E2E2E] p-4"><h2 className="font-heading font-semibold">Source health</h2></div>
          <State state={health} isEmpty={!(health.data?.sources || []).length}
            empty={<p className="p-5 text-sm text-slate-400">No collector observations stored yet.</p>}>
            <div className="flex flex-wrap gap-2 p-4">
              {(health.data?.sources || []).map((source, index) => (
                <span key={index} className="rounded-md border border-[#3A3A3A] px-2 py-1 font-mono text-[11px] text-slate-300">
                  {source.provider} · {source.asset_class} · {source.state === "recent_observation" ? "recent" : "stale"} · {source.age_minutes}m
                </span>
              ))}
            </div>
          </State>
          <p className="border-t border-[#2E2E2E] px-4 py-3 text-xs text-slate-500">
            Observation recency only, not a provider SLA and not proof that a market is open.
          </p>
        </div>
      </div>
    </div>
  );
}

function CryptoScanner({ onWatch }) {
  const [state, load] = useRequest();
  const [symbols, setSymbols] = useState(CRYPTO_UNIVERSE.slice(0, 6).join(","));
  const [granularity, setGranularity] = useState("60");
  const [query, setQuery] = useState("");
  const [signalsOnly, setSignalsOnly] = useState(false);

  const run = useCallback(() => {
    const parsed = parseSymbols(symbols, { universe: CRYPTO_UNIVERSE });
    if (parsed.error) return toast.error(parsed.error);
    load(`/api/v1/intelligence/scanners/crypto?symbols=${encodeURIComponent(parsed.symbols.join(","))}&granularity=${granularity}`);
  }, [symbols, granularity, load]);

  // Run once on mount; changing the fields requires an explicit scan.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, []);

  const rows = useMemo(
    () => sortRows(filterRows(state.data?.rows || [], { query, signalsOnly }), "attention_score", "desc"),
    [state.data, query, signalsOnly]);

  return (
    <div className={card}>
      <ScanToolbar onRun={run} loading={state.loading} label="Scan crypto">
        <div>
          <Label className="label-mono" htmlFor="crypto-symbols">Symbols</Label>
          <Input id="crypto-symbols" value={symbols} onChange={(event) => setSymbols(event.target.value)}
            className="mt-1 w-64 border-[#3A3A3A] bg-[#080808] font-mono" />
        </div>
        <div>
          <Label className="label-mono">Candle size</Label>
          <Select value={granularity} onValueChange={setGranularity}>
            <SelectTrigger className="mt-1 w-28 border-[#3A3A3A] bg-[#080808]"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] text-white">
              <SelectItem value="60">1m</SelectItem>
              <SelectItem value="300">5m</SelectItem>
              <SelectItem value="900">15m</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <MetricFilters query={query} setQuery={setQuery} signalsOnly={signalsOnly} setSignalsOnly={setSignalsOnly} />
      </ScanToolbar>
      <div className="flex flex-wrap gap-1 px-4 pt-3">
        {CRYPTO_UNIVERSE.map((symbol) => (
          <button key={symbol} type="button"
            onClick={() => {
              const current = parseSymbols(symbols).symbols;
              const next = current.includes(symbol) ? current.filter((s) => s !== symbol) : [...current, symbol];
              setSymbols(next.slice(0, 8).join(","));
            }}
            className={`rounded border px-2 py-1 font-mono text-[11px] ${parseSymbols(symbols).symbols.includes(symbol) ? "border-[#2F8CFF] text-[#2F8CFF]" : "border-[#3A3A3A] text-slate-400"}`}>
            {symbol}
          </button>
        ))}
      </div>
      <ScanTable rows={rows} loading={state.loading} error={state.error} status={state.status}
        emptyMessage={state.data?.data_status === "provider_unavailable"
          ? "The public candle provider returned no usable bars; nothing is shown rather than guessed."
          : "No symbols matched the current filter."}
        source={<Attribution data={state.data} />} />
      {rows.length > 0 && (
        <div className="flex flex-wrap gap-2 border-t border-[#2E2E2E] p-3">
          {rows.slice(0, 6).map((row) => (
            <div key={row.symbol} className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-slate-400">{row.symbol}</span>
              <QuickWatch onWatch={() => onWatch(row.symbol)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StockScanner({ onWatch }) {
  const [state, load] = useRequest();
  const [symbols, setSymbols] = useState("AAPL,MSFT,NVDA,SPY,QQQ,TSLA");
  const [query, setQuery] = useState("");
  const [signalsOnly, setSignalsOnly] = useState(false);

  const run = useCallback(() => {
    const parsed = parseSymbols(symbols);
    if (parsed.error) return toast.error(parsed.error);
    load(`/api/v1/intelligence/scanners/stocks?symbols=${encodeURIComponent(parsed.symbols.join(","))}`);
  }, [symbols, load]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, []);

  const rows = useMemo(
    () => sortRows(filterRows(state.data?.rows || [], { query, signalsOnly }), "attention_score", "desc"),
    [state.data, query, signalsOnly]);
  const unavailable = ["provider_not_configured", "provider_unavailable", "disabled_by_admin"].includes(state.data?.data_status);

  return (
    <div className={card}>
      <ScanToolbar onRun={run} loading={state.loading} label="Scan stocks">
        <div>
          <Label className="label-mono" htmlFor="stock-symbols">Symbols</Label>
          <Input id="stock-symbols" value={symbols} onChange={(event) => setSymbols(event.target.value)}
            className="mt-1 w-72 border-[#3A3A3A] bg-[#080808] font-mono" />
        </div>
        <MetricFilters query={query} setQuery={setQuery} signalsOnly={signalsOnly} setSignalsOnly={setSignalsOnly} />
      </ScanToolbar>
      {unavailable && !state.loading ? (
        <div className="space-y-2 p-5">
          <p className="flex items-center gap-2 font-semibold text-amber-300">
            <ShieldAlert className="h-4 w-4" /> Stock scanner is not connected
          </p>
          <p className="text-sm text-slate-400">
            {state.data?.note || "No authorized stock market-data provider is available on this server."}
          </p>
          {state.data?.required_env?.length > 0 && (
            <p className="font-mono text-xs text-slate-500">Server operator must set: {state.data.required_env.join(", ")}</p>
          )}
          <p className="text-xs text-slate-500">
            KAOS does not scrape exchanges or display simulated quotes, so no rows are shown until Alpaca
            market-data keys are configured.
          </p>
        </div>
      ) : (
        <ScanTable rows={rows} loading={state.loading} error={state.error} status={state.status}
          emptyMessage="No stock rows matched. Markets may be closed or the filter is too narrow."
          source={<Attribution data={state.data} />} />
      )}
      {rows.length > 0 && (
        <div className="flex flex-wrap gap-2 border-t border-[#2E2E2E] p-3">
          {rows.slice(0, 6).map((row) => (
            <div key={row.symbol} className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-slate-400">{row.symbol}</span>
              <QuickWatch onWatch={() => onWatch(row.symbol)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SocialScanner() {
  const [state, load] = useRequest();
  const [windowMinutes, setWindowMinutes] = useState("60");
  const run = useCallback(() => load(`/api/v1/intelligence/scanners/social?window_minutes=${windowMinutes}`), [windowMinutes, load]);
  useEffect(() => { run(); }, [run]);

  return (
    <div className={card}>
      <ScanToolbar onRun={run} loading={state.loading} label="Refresh social">
        <div>
          <Label className="label-mono">Window</Label>
          <Select value={windowMinutes} onValueChange={setWindowMinutes}>
            <SelectTrigger className="mt-1 w-32 border-[#3A3A3A] bg-[#080808]"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] text-white">
              <SelectItem value="60">60 minutes</SelectItem>
              <SelectItem value="240">4 hours</SelectItem>
              <SelectItem value="1440">24 hours</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <p className="max-w-md pb-1 text-xs text-slate-500">
          Counts are stored KAOS observations per ticker, not platform-wide mentions. A mention is not a recommendation.
        </p>
      </ScanToolbar>
      <State state={state} isEmpty={!(state.data?.rows || []).length}
        empty={
          <div className="p-5 text-sm text-slate-400">
            <p className="flex items-center gap-2 font-semibold text-slate-300">
              <AlertTriangle className="h-4 w-4 text-amber-400" /> No social observations stored yet
            </p>
            <p className="mt-2">
              The social scanner reads posts already collected by the KAOS collector
              {state.data?.collector_configured ? "" : " (collector key not configured on this server)"}.
              Run the Bluesky collector to populate this view. No synthetic mentions are shown.
            </p>
          </div>
        }>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse">
            <thead>
              <tr className="border-b border-[#2E2E2E]">
                {["Ticker", "Mentions now", "Prior window", "Change", "Velocity", "Providers", "Direction mix", "Latest post", "Source"].map((label) => (
                  <th key={label} className={th}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(state.data?.rows || []).map((row) => (
                <tr key={row.asset} className="border-b border-[#1c1c1c] hover:bg-[#141414]">
                  <td className={`${td} font-semibold text-white`}>{row.asset}</td>
                  <td className={`${td} font-mono`}>{row.mentions_current_window}</td>
                  <td className={`${td} font-mono`}>{row.mentions_prior_window}</td>
                  <td className={`${td} font-mono`}>{formatPct(row.mention_change_pct)}</td>
                  <td className={td}>
                    <Chip tone={row.velocity === "rising" ? "good" : row.velocity === "falling" ? "bear" : "neutral"}>{row.velocity}</Chip>
                  </td>
                  <td className={`${td} font-mono text-xs`}>{row.providers.join(", ") || "—"}</td>
                  <td className={`${td} font-mono text-xs`}>
                    ↑{row.direction_counts?.bullish || 0} ↓{row.direction_counts?.bearish || 0} ·{row.direction_counts?.neutral || 0}
                  </td>
                  <td className={`${td} font-mono text-xs text-slate-500`}>
                    {row.latest_published_at ? new Date(row.latest_published_at).toLocaleString() : "—"}
                  </td>
                  <td className={td}>
                    {/^https:\/\//.test(row.latest_source_url || "") ? (
                      <a href={row.latest_source_url} target="_blank" rel="noopener noreferrer" className="text-[#2F8CFF] hover:underline">
                        Open <ArrowUpRight className="inline h-3 w-3" />
                      </a>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </State>
      <div className="border-t border-[#2E2E2E] px-4 py-3 font-mono text-[11px] text-slate-500">
        {state.data?.counts_meaning} · Providers: {(state.data?.providers_supported || []).join(", ") || "—"}
      </div>
    </div>
  );
}

function OptionsResearch() {
  const [state, load] = useRequest();
  const [underlying, setUnderlying] = useState("SPY");
  const run = useCallback(() => load(`/api/v1/intelligence/options/research?underlying=${encodeURIComponent(underlying.trim().toUpperCase())}`), [underlying, load]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, []);

  return (
    <div className={card}>
      <ScanToolbar onRun={run} loading={state.loading} label="Load options research">
        <div>
          <Label className="label-mono" htmlFor="option-underlying">Underlying</Label>
          <Input id="option-underlying" value={underlying} onChange={(event) => setUnderlying(event.target.value)}
            className="mt-1 w-24 border-[#3A3A3A] bg-[#080808] font-mono" />
        </div>
        <p className="max-w-md pb-1 text-xs text-slate-500">
          Research only. Stored chain snapshots are shown; Greeks and trade-side data are never estimated.
        </p>
      </ScanToolbar>
      <div className="grid gap-3 border-b border-[#2E2E2E] p-4 sm:grid-cols-2">
        <div className="rounded-lg border border-[#3A3A3A] p-3">
          <p className="label-mono">SPY 0DTE snapshot</p>
          <p className="mt-1 text-sm text-slate-300">
            {state.loading ? "Checking…" : state.data?.spy_0dte_available
              ? `${state.data.spy_0dte_rows.length} same-day contract observation(s) stored`
              : "No same-day SPY contract observations are stored."}
          </p>
        </div>
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="label-mono text-amber-300">Metrics not available</p>
          <p className="mt-1 font-mono text-xs text-amber-100/80">
            {(state.data?.metrics_unavailable || ["implied_volatility", "delta", "gamma", "theta", "vega"]).join(", ")}
          </p>
          <p className="mt-1 text-xs text-amber-100/70">{state.data?.unavailable_reason || "An authorized options feed is required."}</p>
        </div>
      </div>
      <State state={state} isEmpty={!(state.data?.rows || []).length}
        empty={
          <div className="p-5 text-sm text-slate-400">
            <p className="font-semibold text-slate-300">No options observations stored</p>
            <p className="mt-2">
              The options collector needs a Tradier market-data token{state.data?.provider_configured ? "" : " (not configured)"}.
              Unusual-activity and 0DTE rows appear only after real chain snapshots are ingested.
            </p>
          </div>
        }>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse">
            <thead>
              <tr className="border-b border-[#2E2E2E]">
                {["Contract", "Root", "Expiry", "Type", "0DTE", "Direction", "Strength", "Observed", "Summary", "Source"].map((label) => (
                  <th key={label} className={th}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(state.data?.rows || []).map((row) => (
                <tr key={`${row.contract}-${row.observed_at}`} className="border-b border-[#1c1c1c] hover:bg-[#141414]">
                  <td className={`${td} font-mono text-xs text-white`}>{row.contract}</td>
                  <td className={`${td} font-mono`}>{row.root || "—"}</td>
                  <td className={`${td} font-mono`}>{row.expiration || "—"}</td>
                  <td className={td}>{row.option_type || "—"}</td>
                  <td className={td}>{row.same_day_expiration ? <Chip tone="good">0DTE</Chip> : "—"}</td>
                  <td className={td}><Chip>{row.direction}</Chip></td>
                  <td className={`${td} font-mono`}>{row.strength == null ? "—" : Number(row.strength).toFixed(2)}</td>
                  <td className={`${td} font-mono text-xs text-slate-500`}>{new Date(row.observed_at).toLocaleString()}</td>
                  <td className="max-w-[320px] whitespace-normal px-3 py-3 text-xs text-slate-400">{row.summary}</td>
                  <td className={td}>
                    {/^https:\/\//.test(row.source_url || "") ? (
                      <a href={row.source_url} target="_blank" rel="noopener noreferrer" className="text-[#2F8CFF] hover:underline">
                        Source <ArrowUpRight className="inline h-3 w-3" />
                      </a>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </State>
      <Attribution data={state.data} />
    </div>
  );
}

function WatchlistsAndAlerts({ refreshSignal }) {
  const [watchState, loadWatch] = useRequest();
  const [alertState, loadAlerts] = useRequest();
  const [listName, setListName] = useState("");
  const [symbolDrafts, setSymbolDrafts] = useState({});
  const [alertForm, setAlertForm] = useState({ name: "", kind: "breakout_20", symbol: "BTC-USD", threshold: "", signal_code: "BREAKOUT_20" });
  const [checkResult, setCheckResult] = useState(null);

  const reload = useCallback(() => {
    loadWatch("/api/v1/intelligence/watchlists");
    loadAlerts("/api/v1/intelligence/alerts");
  }, [loadWatch, loadAlerts]);

  useEffect(() => { reload(); }, [reload, refreshSignal]);

  const createList = async () => {
    try {
      await api.post("/api/v1/intelligence/watchlists", { name: listName });
      setListName("");
      toast.success("Watchlist created");
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const addSymbol = async (list) => {
    const draft = symbolDrafts[list.id] || "";
    try {
      await api.post(`/api/v1/intelligence/watchlists/${list.id}/symbols`, { symbol: draft });
      setSymbolDrafts({ ...symbolDrafts, [list.id]: "" });
      toast.success(`${draft.toUpperCase()} added`);
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const removeSymbol = async (list, symbol) => {
    try {
      await api.delete(`/api/v1/intelligence/watchlists/${list.id}/symbols/${encodeURIComponent(symbol)}`);
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const deleteList = async (list) => {
    try {
      await api.delete(`/api/v1/intelligence/watchlists/${list.id}`);
      toast.success("Watchlist deleted");
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const createAlert = async () => {
    const built = buildAlertPayload(alertForm);
    if (!built.ok) return toast.error(built.error);
    try {
      await api.post("/api/v1/intelligence/alerts", built.payload);
      toast.success("Alert saved");
      setAlertForm({ ...alertForm, name: "" });
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const deleteAlert = async (alert) => {
    try {
      await api.delete(`/api/v1/intelligence/alerts/${alert.id}`);
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const runChecks = async () => {
    try {
      const { data } = await api.post("/api/v1/intelligence/alerts/evaluate");
      setCheckResult(data);
      toast.success(`${data.triggered.length} of ${data.evaluated} alert(s) triggered`);
      reload();
    } catch (error) { toast.error(errMsg(error)); }
  };

  const kind = ALERT_KINDS.find((entry) => entry.value === alertForm.kind) || ALERT_KINDS[0];

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className={card}>
        <div className="border-b border-[#2E2E2E] p-4">
          <h2 className="font-heading font-semibold">Watchlists</h2>
          <p className="mt-1 text-xs text-slate-500">
            {watchState.data?.limits ? `${watchState.data.limits.lists} lists · ${watchState.data.limits.symbols} symbols each` : "Member-scoped"}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2 border-b border-[#2E2E2E] p-4">
          <div>
            <Label className="label-mono" htmlFor="list-name">New watchlist</Label>
            <Input id="list-name" value={listName} onChange={(event) => setListName(event.target.value)}
              placeholder="Momentum" className="mt-1 w-44 border-[#3A3A3A] bg-[#080808]" />
          </div>
          <Button onClick={createList} disabled={!listName.trim()} className="bg-[#2F8CFF] font-semibold text-white">Create</Button>
        </div>
        <State state={watchState} isEmpty={!(watchState.data?.watchlists || []).length}
          empty={<p className="p-5 text-sm text-slate-400">No watchlists yet.</p>}>
          <div className="divide-y divide-[#1c1c1c]">
            {(watchState.data?.watchlists || []).map((list) => (
              <div key={list.id} className="p-4">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-white">{list.name}</p>
                  <button type="button" onClick={() => deleteList(list)} aria-label={`Delete ${list.name}`}
                    className="text-slate-500 hover:text-[#C62828]"><Trash2 className="h-4 w-4" /></button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(list.symbols || []).length === 0 && <span className="text-xs text-slate-500">Empty</span>}
                  {(list.symbols || []).map((symbol) => (
                    <span key={symbol} className="inline-flex items-center gap-1 rounded border border-[#3A3A3A] px-2 py-0.5 font-mono text-[11px] text-slate-300">
                      {symbol}
                      <button type="button" onClick={() => removeSymbol(list, symbol)} aria-label={`Remove ${symbol}`}
                        className="text-slate-500 hover:text-[#C62828]">×</button>
                    </span>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <Input value={symbolDrafts[list.id] || ""} placeholder="Add symbol"
                    onChange={(event) => setSymbolDrafts({ ...symbolDrafts, [list.id]: event.target.value })}
                    className="h-8 w-36 border-[#3A3A3A] bg-[#080808] font-mono text-xs" />
                  <Button size="sm" onClick={() => addSymbol(list)} className="h-8 bg-[#151515] text-slate-200 hover:bg-[#1f1f1f]">Add</Button>
                </div>
              </div>
            ))}
          </div>
        </State>
      </div>

      <div className={card}>
        <div className="flex items-center justify-between border-b border-[#2E2E2E] p-4">
          <div>
            <h2 className="font-heading font-semibold">Research alerts</h2>
            <p className="mt-1 text-xs text-slate-500">Checked on demand against completed bars and stored social data.</p>
          </div>
          <Button onClick={runChecks} size="sm" className="bg-[#2F8CFF] font-semibold text-white">Run checks</Button>
        </div>
        <div className="grid gap-2 border-b border-[#2E2E2E] p-4 sm:grid-cols-2">
          <div>
            <Label className="label-mono" htmlFor="alert-name">Name</Label>
            <Input id="alert-name" value={alertForm.name} onChange={(event) => setAlertForm({ ...alertForm, name: event.target.value })}
              className="mt-1 border-[#3A3A3A] bg-[#080808]" placeholder="BTC breakout" />
          </div>
          <div>
            <Label className="label-mono">Type</Label>
            <Select value={alertForm.kind} onValueChange={(value) => setAlertForm({ ...alertForm, kind: value })}>
              <SelectTrigger className="mt-1 border-[#3A3A3A] bg-[#080808]"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] text-white">
                {ALERT_KINDS.map((entry) => <SelectItem key={entry.value} value={entry.value}>{entry.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="label-mono" htmlFor="alert-symbol">Symbol</Label>
            <Input id="alert-symbol" value={alertForm.symbol} onChange={(event) => setAlertForm({ ...alertForm, symbol: event.target.value })}
              className="mt-1 border-[#3A3A3A] bg-[#080808] font-mono" placeholder="BTC-USD" />
          </div>
          {kind.needsThreshold && (
            <div>
              <Label className="label-mono" htmlFor="alert-threshold">Price threshold</Label>
              <Input id="alert-threshold" type="number" min="0" value={alertForm.threshold}
                onChange={(event) => setAlertForm({ ...alertForm, threshold: event.target.value })}
                className="mt-1 border-[#3A3A3A] bg-[#080808] font-mono" />
            </div>
          )}
          {alertForm.kind === "signal" && (
            <div>
              <Label className="label-mono">Signal</Label>
              <Select value={alertForm.signal_code} onValueChange={(value) => setAlertForm({ ...alertForm, signal_code: value })}>
                <SelectTrigger className="mt-1 border-[#3A3A3A] bg-[#080808]"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[#0F0F0F] text-white">
                  {SIGNAL_CODES.map((code) => <SelectItem key={code} value={code}>{code}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="flex items-end">
            <Button onClick={createAlert} className="bg-[#22C55E] font-semibold text-black">Save alert</Button>
          </div>
        </div>
        <State state={alertState} isEmpty={!(alertState.data?.alerts || []).length}
          empty={<p className="p-5 text-sm text-slate-400">No alerts configured.</p>}>
          <div className="divide-y divide-[#1c1c1c]">
            {(alertState.data?.alerts || []).map((alert) => (
              <div key={alert.id} className="flex items-start justify-between gap-3 p-4">
                <div>
                  <p className="font-semibold text-white">{alert.name}</p>
                  <p className="mt-1 font-mono text-xs text-slate-400">
                    {alert.kind.replace(/_/g, " ")}{alert.symbol ? ` · ${alert.symbol}` : ""}
                    {alert.threshold != null ? ` · ${alert.threshold}` : ""}
                    {alert.signal_code ? ` · ${alert.signal_code}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {alert.last_triggered_at
                      ? `Last triggered ${new Date(alert.last_triggered_at).toLocaleString()}`
                      : "Not triggered yet"}
                  </p>
                </div>
                <button type="button" onClick={() => deleteAlert(alert)} aria-label={`Delete ${alert.name}`}
                  className="text-slate-500 hover:text-[#C62828]"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </State>
        {checkResult && (
          <div className="border-t border-[#2E2E2E] p-4">
            <p className="label-mono">Last check</p>
            {checkResult.triggered.length === 0 ? (
              <p className="mt-1 text-sm text-slate-400">No alert conditions matched. {checkResult.note}</p>
            ) : (
              <ul className="mt-1 space-y-1 text-sm text-slate-300">
                {checkResult.triggered.map((item) => <li key={item.alert_id}>• {item.reason}</li>)}
              </ul>
            )}
          </div>
        )}
        <p className="border-t border-[#2E2E2E] px-4 py-3 text-xs text-slate-500">
          Alerts create in-app notifications only and never place orders. Delivery runs when you press Run checks.
        </p>
      </div>
    </div>
  );
}

export default function MarketIntelligence() {
  const [tab, setTab] = useState("overview");
  const [catalog, loadCatalog] = useRequest();
  const [health, loadHealth] = useRequest();
  const [radar, loadRadar] = useRequest();
  const [refreshSignal, setRefreshSignal] = useState(0);

  const loadOverview = useCallback(() => {
    loadCatalog("/api/v1/intelligence/center/catalog");
    loadHealth("/api/v1/intelligence/health");
    loadRadar("/api/v1/intelligence/opportunities?limit=8");
  }, [loadCatalog, loadHealth, loadRadar]);

  useEffect(() => { loadOverview(); }, [loadOverview]);

  const quickWatch = useCallback(async (symbol) => {
    try {
      let list = (await api.get("/api/v1/intelligence/watchlists")).data.watchlists?.[0];
      if (!list) {
        list = (await api.post("/api/v1/intelligence/watchlists", { name: "Market Intelligence" })).data;
      }
      await api.post(`/api/v1/intelligence/watchlists/${list.id}/symbols`, { symbol });
      toast.success(`${symbol} added to ${list.name}`);
      setRefreshSignal((value) => value + 1);
    } catch (error) { toast.error(errMsg(error)); }
  }, []);

  const permissionWarning = catalog.status === 403;

  return (
    <section className="space-y-6" data-testid="kaos-market-intelligence">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="label-mono text-[#2F8CFF]">KAOS Intelligence</p>
          <h1 className="mt-1 font-heading text-3xl font-bold text-white">Market Intelligence Center</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Technical, crypto, social and options research in one place. Every row carries its source and
            timestamp, scores rank research attention only, and nothing here can submit a broker order.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip tone="good">Research only</Chip>
          <Chip tone="neutral">No order execution</Chip>
          <Chip tone="warn">Scores ≠ probabilities</Chip>
        </div>
      </header>

      <nav className="flex gap-1 overflow-x-auto rounded-lg border border-[#2E2E2E] bg-[#0A0A0A] p-1" aria-label="Intelligence sections">
        {TABS.map(([key, label, Icon]) => (
          <button key={key} type="button" onClick={() => setTab(key)} aria-pressed={tab === key}
            className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm transition ${tab === key ? "bg-[#2F8CFF]/10 text-[#2F8CFF]" : "text-slate-400 hover:bg-[#111111] hover:text-white"}`}>
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </nav>

      {permissionWarning && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          Market Intelligence scanners require a Pro or Ultimate membership.{" "}
          <Link to="/dashboard/subscription" className="underline">Review plans →</Link>
        </div>
      )}

      {tab === "overview" && <Overview catalog={catalog} health={health} radar={radar} onRefresh={loadOverview} />}
      {tab === "crypto" && <CryptoScanner onWatch={quickWatch} />}
      {tab === "stocks" && <StockScanner onWatch={quickWatch} />}
      {tab === "social" && <SocialScanner />}
      {tab === "options" && <OptionsResearch />}
      {tab === "watch" && <WatchlistsAndAlerts refreshSignal={refreshSignal} />}

      <div className="rounded-lg border border-[#2E2E2E] bg-[#0A0A0A] p-4 text-xs text-slate-500">
        <p>
          KAOS Market Intelligence is research software. Data may be delayed, sampled or unavailable;
          social coverage is limited to collected sources; options Greeks are only shown when an authorized feed
          provides them. Nothing here is financial advice, and no score is a promise of profit.
        </p>
      </div>
    </section>
  );
}
