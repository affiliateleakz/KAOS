import React, { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";

const BROKERS = [
  ["coinbase", "Coinbase Advanced", "https://advanced.coinbase.com/", "API integration"],
  ["pocketoption", "Pocket Option", "https://pocketoption.com/", "Extension integration"],
  ["kraken", "Kraken", "https://www.kraken.com/", "Adapter pending"],
  ["ibkr", "Interactive Brokers", "https://www.interactivebrokers.com/", "Gateway adapter pending"],
  ["alpaca", "Alpaca", "https://alpaca.markets/", "Adapter pending"],
  ["oanda", "OANDA", "https://www.oanda.com/", "Adapter pending"],
  ["tradier", "Tradier", "https://tradier.com/", "Adapter pending"],
  ["tastytrade", "tastytrade", "https://tastytrade.com/", "Adapter pending"],
  ["binanceus", "Binance.US", "https://www.binance.us/", "Adapter pending"],
  ["schwab", "Charles Schwab", "https://www.schwab.com/", "Adapter pending"],
];
export default function BrokerConnections() {
  const [saved, setSaved] = useState({});
  const [form, setForm] = useState({key_name:"", private_key:""});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    try {
      const r = await api.get("/api/v1/broker-connections");
      setSaved(Object.fromEntries((r.data.connections || []).map(x => [x.broker, x])));
    } catch(e) { setError(`Connection status unavailable: ${errMsg(e)}`); }
  }, []);
  const [acct, setAcct] = useState(null);
  const [acctErr, setAcctErr] = useState("");
  const loadAccount = useCallback(async () => {
    try { const r = await api.get("/api/v1/broker-connections/coinbase/accounts"); setAcct(r.data); setAcctErr(""); }
    catch(e) { if (e?.response?.status === 404) setAcct(null); else setAcctErr(errMsg(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!saved.coinbase?.verified) { setAcct(null); return undefined; }
    loadAccount();
    const t = setInterval(() => { if (!document.hidden) loadAccount(); }, 15000);
    return () => clearInterval(t);
  }, [saved.coinbase?.verified, loadAccount]);
  async function save(e) {
    e.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      await api.put("/api/v1/broker-connections/coinbase", form);
      setForm({key_name:"", private_key:""});
      setNotice("Coinbase verified and saved to your KAOS account.");
      await load();
    } catch(e) { setError(`Coinbase connection failed: ${errMsg(e)}`); }
    finally { setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm("Disconnect Coinbase from your KAOS account?")) return;
    setBusy(true); setError("");
    try { await api.delete("/api/v1/broker-connections/coinbase"); await load(); setNotice("Coinbase disconnected."); }
    catch(e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  }
  return <section className="mx-auto max-w-4xl space-y-6 text-white" data-testid="member-broker-connections">
    <div><h1 className="text-2xl font-bold">KAOS Broker Connections</h1><p className="mt-2 text-sm text-slate-400">Manage broker access for your KAOS membership. Saved credentials remain encrypted on the website backend and are not returned to your extension.</p></div>
    {error && <p role="alert" className="rounded border border-red-600 p-3 text-red-300">{error}</p>}
    {notice && <p role="status" className="rounded border border-green-700 p-3 text-green-300">{notice}</p>}
    <div className="grid gap-3 md:grid-cols-2">{BROKERS.map(([id,name,url,status]) => <div key={id} className="rounded-lg border border-slate-700 bg-[#111] p-4">
      <div className="flex items-center justify-between gap-2"><h2 className="font-semibold">{name}</h2><span className="text-xs text-slate-400">{saved[id]?.verified ? "Verified & saved" : saved[id]?.saved ? "Saved" : status}</span></div>
      <a href={url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm text-[#2F8CFF]">Open broker website ↗</a>
    </div>)}</div>
    <div className="rounded-lg border border-slate-700 bg-[#111] p-5"><h2 className="mb-2 text-xl font-semibold">Coinbase Advanced API</h2>
      <p className="mb-4 text-sm text-slate-400">{saved.coinbase?.saved ? `Saved key ending ${saved.coinbase.key_hint || "••••"}. Update it below or disconnect.` : "Enter your Coinbase Consumer / Advanced Trade CDP credentials once."}</p>
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm">API key name<input autoComplete="off" required value={form.key_name} onChange={e=>setForm({...form,key_name:e.target.value})} placeholder="organizations/.../apiKeys/..." className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <label className="block text-sm">Private key<textarea autoComplete="off" required value={form.private_key} onChange={e=>setForm({...form,private_key:e.target.value})} rows={4} placeholder="Paste the original Coinbase key" className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <button disabled={busy} className="rounded bg-[#2F8CFF] px-4 py-2 font-semibold text-black disabled:opacity-50">{busy ? "Verifying…" : "Verify & save Coinbase"}</button>
        {saved.coinbase?.saved && <button type="button" disabled={busy} onClick={disconnect} className="ml-3 rounded border border-red-700 px-4 py-2 text-red-300 disabled:opacity-50">Disconnect</button>}
      </form>
      <p className="mt-4 text-xs text-slate-400">View permission is required; Trade is optional (KAOS live order submission is disabled until the owner authorizes it). Keys with Transfer permission are refused.</p>
    </div>
    {saved.coinbase?.verified && <CoinbaseAccount acct={acct} err={acctErr} onRefresh={loadAccount} />}
    <p className="text-xs text-slate-400">Broker names marked “Adapter pending” are not available for automated trading yet. Selecting a broker does not imply that live trading is supported.</p>
  </section>;
}

function Table({ cols, rows, empty, testid }) {
  return <div className="overflow-x-auto"><table data-testid={testid} className="w-full text-left text-sm">
    <thead className="text-xs uppercase text-slate-400"><tr>{cols.map(([k, l]) => <th key={k} className="py-1 pr-3">{l}</th>)}</tr></thead>
    <tbody>{rows.length ? rows.map((r, i) => <tr key={i} className="border-t border-slate-800">{cols.map(([k]) => <td key={k} className="py-1 pr-3 font-mono">{r[k] ?? "–"}</td>)}</tr>)
      : <tr><td colSpan={cols.length} className="py-2 text-slate-500">{empty}</td></tr>}</tbody>
  </table></div>;
}

function CoinbaseAccount({ acct, err, onRefresh }) {
  return <div className="rounded-lg border border-[#2F8CFF]/60 bg-[#0b0f17] p-5" data-testid="coinbase-account">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-xl font-semibold">Coinbase account (read-only)</h2>
      <button type="button" onClick={onRefresh} className="rounded border border-slate-600 px-3 py-1 text-sm">Refresh</button>
    </div>
    <p className="mb-4 text-xs text-slate-400">{acct ? `Live from Coinbase Advanced API · key ${acct.key_hint} · fetched ${new Date(acct.fetched_at).toLocaleTimeString()} · refreshes every 15 s` : "Loading from Coinbase…"} · KAOS does not place orders on this account.</p>
    {err && <p role="alert" className="mb-3 rounded border border-amber-600 p-2 text-sm text-amber-300">Coinbase unavailable: {err}{acct ? " (showing last loaded data)" : ""}</p>}
    {acct && <div className="space-y-5">
      <div><h3 className="mb-1 font-semibold">Balances</h3><Table testid="cb-balances" cols={[["currency", "Asset"], ["available", "Available"], ["hold", "On hold"]]} rows={acct.balances} empty="No non-zero balances" /></div>
      <div><h3 className="mb-1 font-semibold">Open orders</h3><Table testid="cb-open-orders" cols={[["product_id", "Market"], ["side", "Side"], ["order_type", "Type"], ["status", "Status"], ["filled_size", "Filled"], ["created_time", "Created"]]} rows={acct.open_orders} empty="No open orders" /></div>
      <div><h3 className="mb-1 font-semibold">Recent fills</h3><Table testid="cb-fills" cols={[["product_id", "Market"], ["side", "Side"], ["size", "Size"], ["price", "Price"], ["commission", "Fee"], ["trade_time", "Time"]]} rows={acct.fills} empty="No fills yet" /></div>
      <p className="text-sm text-slate-300">Fee tier: <b>{acct.fees.tier || "–"}</b> · maker {acct.fees.maker_rate ?? "–"} · taker {acct.fees.taker_rate ?? "–"} · 30-day fees {acct.fees.total_fees ?? "–"}</p>
    </div>}
  </div>;
}
