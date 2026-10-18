import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";

const H = ({ children }) => <h1 className="mb-6 font-heading text-2xl font-bold tracking-wide">{children}</h1>;

export function TradingOps() {
  const [t, setT] = useState(null);
  const [trades, setTrades] = useState([]);
  const [strat, setStrat] = useState(null);
  const [models, setModels] = useState([]);
  useEffect(() => {
    api.get("/api/admin/trading/telemetry").then((r) => setT(r.data)).catch(() => {});
    api.get("/api/admin/trading/trades").then((r) => setTrades(r.data)).catch(() => {});
    api.get("/api/admin/official-strategy").then((r) => setStrat(r.data)).catch(() => {});
    api.get("/api/admin/ai-models").then((r) => setModels(r.data)).catch(() => {});
  }, []);
  if (!t) return <p className="text-slate-500">Loading…</p>;
  const cards = [["Signals", t.signals], ["Order Attempts", t.orderAttempts], ["Broker Confirmed", t.brokerConfirmed],
    ["Failed", t.failed], ["Results", t.results], ["Win Rate", t.winRate != null ? t.winRate + "%" : "—"], ["Net P/L", t.netPnl]];
  return (
    <div>
      <H>Trading Operations</H>
      <div className="mb-4 rounded-lg border border-[#2E2E2E] bg-[#0c0c0c] p-3 text-xs text-slate-500">Aggregate telemetry across all members. Records flagged SIM are simulated demo data.</div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        {cards.map(([l, v]) => (<div key={l} className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-2xl font-bold text-[#2F8CFF]">{v}</div></div>))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        {[["By Engine", t.byEngine], ["By Mode", t.byMode], ["By Result", t.byResult], ["By Failure", t.byFailure]].map(([l, obj]) => (
          <div key={l} className="card-surface p-4"><div className="label-mono mb-2">{l}</div>
            {Object.keys(obj || {}).length === 0 ? <p className="text-xs text-slate-500">—</p> :
              Object.entries(obj).map(([k, v]) => <div key={k} className="flex justify-between border-b border-[#2E2E2E] py-1 font-mono text-xs"><span className="text-slate-400">{k}</span><span className="text-white">{v}</span></div>)}
          </div>
        ))}
      </div>
      {strat && (
        <div className="card-surface mt-6 p-5">
          <h3 className="font-heading font-semibold">Official Strategy &amp; Models</h3>
          <p className="mt-1 font-mono text-xs text-slate-400">{strat.officialStrategy.name} v{strat.officialStrategy.version} · {strat.officialStrategy.structureComponent} · authority: {strat.tradingConfig.executionAuthority}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {strat.officialStrategy.engines.map((e) => <span key={e.key} className="rounded bg-[#0c0c0c] border border-[#2E2E2E] px-2 py-1 font-mono text-xs text-[#2F8CFF]">{e.label} · {e.expiration}</span>)}
          </div>
          <div className="mt-3 font-mono text-xs text-slate-500">AI models: {models.map((m) => `${m.version}(${m.status})`).join(", ") || "none"}</div>
        </div>
      )}
      <div className="card-surface mt-6 p-0 overflow-x-auto">
        <div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Recent Trades</h3></div>
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Asset</TableHead><TableHead>Dir</TableHead><TableHead>Engine</TableHead><TableHead>Mode</TableHead><TableHead>State</TableHead><TableHead>Result</TableHead><TableHead>StratVer</TableHead><TableHead>AIVer</TableHead></TableRow></TableHeader>
          <TableBody>{trades.slice(0, 50).map((tr) => (
            <TableRow key={tr.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-xs">{tr.asset}</TableCell><TableCell className={tr.direction === "BUY" ? "text-[#2F8CFF]" : "text-[#C62828]"}>{tr.direction}</TableCell><TableCell className="font-mono text-xs">{tr.engine || "—"}</TableCell><TableCell className="font-mono text-xs">{tr.tradingMode}</TableCell><TableCell className="font-mono text-xs">{tr.state}{tr.simulated && "·SIM"}</TableCell><TableCell className={tr.result === "WIN" ? "text-[#2F8CFF]" : tr.result === "LOSS" ? "text-[#C62828]" : "text-slate-400"}>{tr.result || tr.failureCode || "—"}</TableCell><TableCell className="font-mono text-xs">{tr.strategyVersion || "—"}</TableCell><TableCell className="font-mono text-xs">{tr.aiModelVersion || "—"}</TableCell></TableRow>
          ))}</TableBody>
        </Table>
      </div>
    </div>
  );
}

const STATUS_COLOR = { SUPPORTED: "text-[#2F8CFF] border-[#2F8CFF]/40 bg-[#2F8CFF]/10", COMING_SOON: "text-amber-300 border-amber-400/40 bg-amber-400/10", PLANNED: "text-slate-400 border-slate-500/40 bg-slate-500/10" };

export function Connectors() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/admin/connectors").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const setStatus = async (c, status) => {
    try { await api.post("/api/admin/connectors", { id: c.id, name: c.name, status, note: c.note || "" }); toast.success("Connector updated"); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div>
      <H>Platform Connectors</H>
      <div className="mb-4 rounded-lg border border-[#2E2E2E] bg-[#0c0c0c] p-3 text-xs text-slate-500">Pocket Option is connector #1. Never mark a connector SUPPORTED until it actually works. Execution semantics (e.g. 15s/30s binary expirations) are platform-specific.</div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {list.map((c) => (
          <div key={c.id} className="card-surface p-5" data-testid={`connector-${c.id}`}>
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-semibold">{c.name}</h3>
              <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase ${STATUS_COLOR[c.status] || ""}`}>{c.status.replace("_", " ")}</span>
            </div>
            <p className="mt-2 text-xs text-slate-400 min-h-[2rem]">{c.note}</p>
            <div className="mt-3">
              <Select value={c.status} onValueChange={(v) => setStatus(c, v)}>
                <SelectTrigger data-testid={`connector-status-${c.id}`} className="bg-[#0c0c0c] border-[#2E2E2E] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[#111] text-white">{["SUPPORTED", "COMING_SOON", "PLANNED"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
