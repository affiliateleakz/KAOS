import React, { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";

const BROKERS = [
  ["coinbase", "Coinbase Advanced", "https://advanced.coinbase.com/", "API integration"],
  ["pocketoption", "Pocket Option", "https://pocketoption.com/", "Extension integration"],
  ["kraken", "Kraken", "https://www.kraken.com/", "Adapter pending"],
  ["ibkr", "Interactive Brokers", "https://www.interactivebrokers.com/", "Gateway adapter pending"],
  ["alpaca", "Alpaca", "https://alpaca.markets/", "API integration (read-only)"],
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
      {saved.coinbase?.verified && <CoinbaseOrders />}
    <AlpacaPanel onChange={load} />
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
    <p className="mb-4 text-xs text-slate-400"><span className="mr-1 rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold text-amber-300">UNVERIFIED: not yet tested against a real Coinbase account</span>{acct ? `Live from Coinbase Advanced API · key ${acct.key_hint} · fetched ${new Date(acct.fetched_at).toLocaleTimeString()} · refreshes every 15 s` : "Loading from Coinbase…"} · KAOS does not place orders on this account.</p>
    {err && <p role="alert" className="mb-3 rounded border border-amber-600 p-2 text-sm text-amber-300">Coinbase unavailable: {err}{acct ? " (showing last loaded data)" : ""}</p>}
    {acct && <div className="space-y-5">
      <p className="text-sm">Buying power (USD + USDC available): <b data-testid="cb-buying-power">${acct.buying_power_usd ?? "–"}</b></p>
      <div><h3 className="mb-1 font-semibold">Positions</h3><Table testid="cb-positions" cols={[["product_id", "Market"], ["quantity", "Quantity"], ["bid", "Bid"], ["market_value", "Value (USD)"], ["avg_cost", "Avg cost"], ["unrealized_pnl", "Unrealized P&L"], ["realized_pnl_recent", "Realized P&L (recent fills)"], ["fees_recent", "Fees (recent fills)"]]} rows={acct.positions || []} empty="No crypto holdings" />
        <p className="mt-1 text-xs text-slate-500">Cost basis comes from your last 50 Coinbase fills. If they don't cover the whole holding, average cost and unrealized P&L are left blank instead of guessed.</p></div>
      <div><h3 className="mb-1 font-semibold">Balances</h3><Table testid="cb-balances" cols={[["currency", "Asset"], ["available", "Available"], ["hold", "On hold"]]} rows={acct.balances} empty="No non-zero balances" /></div>
      <div><h3 className="mb-1 font-semibold">Open orders</h3><Table testid="cb-open-orders" cols={[["product_id", "Market"], ["side", "Side"], ["order_type", "Type"], ["status", "Status"], ["filled_size", "Filled"], ["created_time", "Created"]]} rows={acct.open_orders} empty="No open orders" /></div>
      <div><h3 className="mb-1 font-semibold">Recent fills</h3><Table testid="cb-fills" cols={[["product_id", "Market"], ["side", "Side"], ["size", "Size"], ["price", "Price"], ["commission", "Fee"], ["trade_time", "Time"]]} rows={acct.fills} empty="No fills yet" /></div>
      <p className="text-sm text-slate-300">Fee tier: <b>{acct.fees.tier || "–"}</b> · maker {acct.fees.maker_rate ?? "–"} · taker {acct.fees.taker_rate ?? "–"} · 30-day fees {acct.fees.total_fees ?? "–"}</p>
    </div>}
  </div>;
}

function CoinbaseOrders() {
  const [form, setForm] = useState({ product_id: "BTC-USD", side: "BUY", size: "10" });
  const [preview, setPreview] = useState(null);
  const [orders, setOrders] = useState([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const loadOrders = useCallback(async () => {
    try { const r = await api.get("/api/v1/coinbase-live/orders"); setOrders(r.data.orders); } catch (e) { setMsg(errMsg(e)); }
  }, []);
  useEffect(() => { loadOrders(); const t = setInterval(loadOrders, 15000); return () => clearInterval(t); }, [loadOrders]);
  const runPreview = async (e) => {
    e.preventDefault(); setBusy(true); setMsg(""); setPreview(null);
    const body = { product_id: form.product_id, side: form.side, [form.side === "BUY" ? "quote_size" : "base_size"]: form.size };
    try { const r = await api.post("/api/v1/coinbase-live/preview", body); setPreview(r.data); }
    catch (e2) { setMsg(errMsg(e2)); } finally { setBusy(false); }
  };
  const cancel = async (id) => {
    setMsg("");
    try { const r = await api.post("/api/v1/coinbase-live/cancel", { client_order_id: id }); setMsg(r.data.cancel_success ? "Cancel accepted by Coinbase" : `Cancel refused: ${r.data.failure_reason}`); loadOrders(); }
    catch (e) { setMsg(errMsg(e)); }
  };
  const live = preview?.live_orders_enabled;
  return <div className="rounded-lg border border-slate-700 bg-[#0b0f17] p-5" data-testid="coinbase-orders">
    <h2 className="mb-1 text-xl font-semibold">Coinbase orders</h2>
    <p className="mb-4 text-xs text-slate-400">Preview asks Coinbase what a market order would cost without placing it (needs a key with Trade permission). Real order submission is <b className="text-amber-300">disabled</b> on this server until the owner authorizes a controlled test.</p>
    <form onSubmit={runPreview} className="mb-4 flex flex-wrap items-end gap-3 text-sm">
      <label>Market<input className="ml-2 w-28 rounded bg-slate-900 px-2 py-1" value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value.toUpperCase() })} /></label>
      <label>Side<select className="ml-2 rounded bg-slate-900 px-2 py-1" value={form.side} onChange={e => setForm({ ...form, side: e.target.value })}><option>BUY</option><option>SELL</option></select></label>
      <label>{form.side === "BUY" ? "Amount (USD)" : "Size (base)"}<input className="ml-2 w-24 rounded bg-slate-900 px-2 py-1" value={form.size} onChange={e => setForm({ ...form, size: e.target.value })} /></label>
      <button disabled={busy} className="rounded bg-[#2F8CFF] px-3 py-1 font-semibold text-black disabled:opacity-50">{busy ? "Previewing…" : "Preview order"}</button>
      <button type="button" disabled title="Real order submission is disabled until the owner authorizes controlled testing" className="cursor-not-allowed rounded border border-slate-600 px-3 py-1 text-slate-500">Submit order (disabled)</button>
    </form>
    {msg && <p role="alert" className="mb-3 rounded border border-amber-600 p-2 text-sm text-amber-300">{msg}</p>}
    {preview && <div className="mb-4 rounded border border-slate-700 p-3 text-sm" data-testid="cb-preview">
      <p className="mb-1 font-semibold">Preview only, nothing was placed{live ? "" : " · live submission disabled"}</p>
      <Table cols={[["order_total", "Order total"], ["commission_total", "Fees"], ["best_bid", "Best bid"], ["best_ask", "Best ask"], ["slippage", "Slippage"]]} rows={[preview.preview]} empty="" />
      {preview.preview.errs?.length ? <p className="mt-2 text-amber-300">Coinbase warnings: {preview.preview.errs.join(", ")}</p> : null}
    </div>}
    <h3 className="mb-1 font-semibold">Orders sent by KAOS</h3>
    <div className="overflow-x-auto"><table data-testid="cb-kaos-orders" className="w-full text-left text-sm">
      <thead className="text-xs uppercase text-slate-400"><tr>{["Market", "Side", "Size", "State", "Filled", "Fees", "Created", ""].map(h => <th key={h} className="py-1 pr-3">{h}</th>)}</tr></thead>
      <tbody>{orders.length ? orders.map(o => <tr key={o.client_order_id} className="border-t border-slate-800 font-mono">
        <td className="py-1 pr-3">{o.product_id}</td><td className="pr-3">{o.side}</td><td className="pr-3">{o.quote_size ? `$${o.quote_size}` : o.base_size}</td>
        <td className="pr-3">{o.state}</td><td className="pr-3">{o.filled_size ?? "–"}</td><td className="pr-3">{o.fill_fees ?? "–"}</td><td className="pr-3">{o.created_at?.slice(0, 19).replace("T", " ")}</td>
        <td>{["ACCEPTED", "OPEN", "PARTIAL_FILL_REVIEW"].includes(o.state) && <button onClick={() => cancel(o.client_order_id)} className="rounded border border-red-500 px-2 text-red-300">Cancel</button>}</td>
      </tr>) : <tr><td colSpan={8} className="py-2 text-slate-500">No orders sent by KAOS (live submission has never been enabled)</td></tr>}</tbody>
    </table></div>
  </div>;
}

function AlpacaPanel({ onChange }) {
  const [st, setSt] = useState(null);
  const [form, setForm] = useState({ key_id: "", secret_key: "", environment: "paper" });
  const [acct, setAcct] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const s = (await api.get("/api/v1/broker-connections/alpaca/status")).data; setSt(s);
      if (s.connected) setAcct((await api.get("/api/v1/broker-connections/alpaca/accounts")).data);
      setMsg("");
    } catch (e) { setMsg(errMsg(e)); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  async function save(e) {
    e.preventDefault(); setBusy(true);
    try { await api.put("/api/v1/broker-connections/alpaca", form); setForm({ key_id: "", secret_key: "", environment: form.environment }); await refresh(); onChange?.(); }
    catch (err) { setMsg(errMsg(err)); } finally { setBusy(false); }
  }
  async function disconnect() {
    setBusy(true);
    try { await api.delete("/api/v1/broker-connections/alpaca"); setAcct(null); await refresh(); onChange?.(); }
    catch (err) { setMsg(errMsg(err)); } finally { setBusy(false); }
  }
  const a = acct?.account;
  return <div className="rounded-lg border border-slate-700 bg-[#111] p-5" data-testid="alpaca-panel">
    <h2 className="mb-1 text-xl font-semibold">Alpaca (stocks &amp; ETFs) · read-only</h2>
    <p className="mb-3 text-xs"><span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold text-amber-300">UNVERIFIED: not yet tested against a real Alpaca account</span> <span className="text-slate-400">Alpaca keys can't be limited to read-only, so KAOS never calls Alpaca's order endpoints. Paper account recommended.</span></p>
    {msg && <p role="alert" className="mb-3 rounded border border-amber-600 p-2 text-sm text-amber-300">{msg}</p>}
    {st?.connected ? <p className="mb-3 text-sm text-slate-300">Connected ({st.environment}) · key {st.key_hint} <button disabled={busy} onClick={disconnect} className="ml-2 rounded border border-red-700 px-2 text-red-300">Disconnect</button></p>
      : <form onSubmit={save} className="mb-3 grid gap-2 md:grid-cols-4">
        <input autoComplete="off" required placeholder="API key ID" value={form.key_id} onChange={e => setForm({ ...form, key_id: e.target.value.trim() })} className="rounded border border-slate-600 bg-[#080808] p-2" />
        <input autoComplete="off" type="password" required placeholder="Secret key" value={form.secret_key} onChange={e => setForm({ ...form, secret_key: e.target.value.trim() })} className="rounded border border-slate-600 bg-[#080808] p-2" />
        <select value={form.environment} onChange={e => setForm({ ...form, environment: e.target.value })} className="rounded border border-slate-600 bg-[#080808] p-2"><option value="paper">Paper account</option><option value="live">Live account (view only)</option></select>
        <button disabled={busy} className="rounded bg-[#2F8CFF] px-3 py-2 font-semibold text-black disabled:opacity-50">{busy ? "Verifying…" : "Verify & save Alpaca"}</button>
      </form>}
    {a && <div className="space-y-4">
      <p className="text-sm">Status {a.status} · cash <b>${a.cash}</b> · buying power <b data-testid="alpaca-buying-power">${a.buying_power}</b> · equity <b>${a.equity}</b></p>
      <div><h3 className="mb-1 font-semibold">Positions</h3><Table testid="alpaca-positions" cols={[["symbol", "Symbol"], ["qty", "Qty"], ["avg_entry_price", "Avg entry"], ["current_price", "Price"], ["market_value", "Value"], ["unrealized_pl", "Unrealized P&L"]]} rows={acct.positions} empty="No positions" /></div>
      <div><h3 className="mb-1 font-semibold">Open orders</h3><Table testid="alpaca-open-orders" cols={[["symbol", "Symbol"], ["side", "Side"], ["type", "Type"], ["qty", "Qty"], ["status", "Status"], ["submitted_at", "Submitted"]]} rows={acct.open_orders} empty="No open orders" /></div>
      <div><h3 className="mb-1 font-semibold">Recent fills</h3><Table testid="alpaca-fills" cols={[["symbol", "Symbol"], ["side", "Side"], ["qty", "Qty"], ["price", "Price"], ["transaction_time", "Time"]]} rows={acct.fills} empty="No fills yet" /></div>
      <p className="text-xs text-slate-500">{acct.fees_note}</p>
    </div>}
  </div>;
}
