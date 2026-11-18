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
  const [preferredBroker, setPreferredBroker] = useState("");
  useEffect(() => { api.get("/api/v1/broker-selection").then(r => setPreferredBroker(r.data.broker || "")).catch(() => {}); }, []);
  const selectPreferredBroker = async (broker) => {
    try {
      await api.put("/api/v1/broker-selection", { broker });
      setPreferredBroker(broker);
      setNotice("Preferred broker saved. This does not enable trading or verify an account.");
    } catch (e) { setError(errMsg(e)); }
  };
  const [saved, setSaved] = useState({});
  const [form, setForm] = useState({key_name:"", private_key:""});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [markets, setMarkets] = useState(null);
  async function checkMarkets() {
    setBusy(true); setError("");
    try { setMarkets((await api.get("/api/v1/broker-connections/coinbase/products")).data); }
    catch(e) { setError(`Coinbase markets unavailable: ${errMsg(e)}`); }
    finally { setBusy(false); }
  }
  const load = useCallback(async () => {
    try {
      const r = await api.get("/api/v1/broker-connections");
      setSaved(Object.fromEntries((r.data.connections || []).map(x => [x.broker, x])));
    } catch(e) { setError(`Connection status unavailable: ${errMsg(e)}`); }
  }, []);
  useEffect(() => { load(); }, [load]);
  async function save(e) {
    e.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      await api.put("/api/v1/broker-connections/coinbase", form);
      setForm({key_name:"", private_key:""});
      setMarkets(null); setNotice("Coinbase read access verified and encrypted credentials saved. Live trading remains disabled.");
      await load();
    } catch(e) { setError(`Coinbase connection failed: ${errMsg(e)}`); }
    finally { setBusy(false); }
  }
  async function disconnect() {
    if (!window.confirm("Disconnect Coinbase from your KAOS account?")) return;
    setBusy(true); setError("");
    try { await api.delete("/api/v1/broker-connections/coinbase"); await load(); setMarkets(null); setNotice("Coinbase disconnected."); }
    catch(e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  }
  return <section className="mx-auto max-w-4xl space-y-6 text-white" data-testid="member-broker-connections">
    <div><h1 className="text-2xl font-bold">KAOS Broker Connections</h1><p className="mt-2 text-sm text-slate-400">Manage broker access for your KAOS membership. Saved credentials remain encrypted on the website backend and are not returned to your extension.</p></div>
    <div className="card-surface p-4">
      <label htmlFor="preferred-broker" className="mb-2 block text-sm font-semibold">Your selected broker</label>
      <select id="preferred-broker" value={preferredBroker} onChange={e => selectPreferredBroker(e.target.value)}
        className="w-full rounded border border-slate-600 bg-[#111] p-2 text-sm">
        <option value="" disabled>Select a broker</option>
        {BROKERS.map(([id,name]) => <option key={id} value={id}>{name}</option>)}
      </select>
      <p className="mt-2 text-xs text-slate-400">Selection is saved to your KAOS account; available trading features depend on a verified broker integration. Live orders require separate consent.</p>
    </div>
    {error && <p role="alert" className="rounded border border-red-600 p-3 text-red-300">{error}</p>}
    {notice && <p role="status" className="rounded border border-green-700 p-3 text-green-300">{notice}</p>}
    <div className="grid gap-3 md:grid-cols-2">{BROKERS.map(([id,name,url,status]) => <div key={id} className="rounded-lg border border-slate-700 bg-[#111] p-4">
      <div className="flex items-center justify-between gap-2"><h2 className="font-semibold">{name}</h2><span className="text-xs text-slate-400">{saved[id]?.verified ? "Verified & saved" : saved[id]?.saved ? "Saved" : status}</span></div>
      <a href={url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm text-[#D4AF37]">Open broker website ↗</a>
    </div>)}</div>
    <div className="rounded-lg border border-slate-700 bg-[#111] p-5"><h2 className="mb-2 text-xl font-semibold">Coinbase Advanced API</h2>
      <p className="mb-4 text-sm text-slate-400">{saved.coinbase?.saved ? `Saved key ending ${saved.coinbase.key_hint || "••••"}. Update it below or disconnect.` : "Enter your Coinbase Consumer / Advanced Trade CDP credentials once."}</p>
      <p className="mb-4 text-sm text-[#D4AF37]">Read-only setup · no orders or transfers. Account verification does not certify the trading bot for Coinbase.</p>
      {saved.coinbase?.saved && <div className="mb-4 space-y-2"><p className="text-xs text-slate-400">Last verified: {saved.coinbase.verified_at ? new Date(saved.coinbase.verified_at).toLocaleString() : 'Not recorded'}. Saved verification is not a continuous connection check.</p><button type="button" disabled={busy} onClick={checkMarkets} className="rounded border border-[#8b6b32] px-4 py-2 text-[#D4AF37] disabled:opacity-50">Check Coinbase markets</button></div>}
      {markets && <div className="mb-4 rounded border border-[#66512d] p-3" data-testid="coinbase-markets"><p className="text-sm text-[#D4AF37]">USD spot market sample · read-only</p><p className="mt-2 text-sm">{markets.products?.map(p=>p.product_id).join(', ') || 'No USD spot products in this sample.'}</p><p className="mt-2 text-xs text-slate-400">This is a partial catalog, not a buy signal or trading permission.</p></div>}
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm">API key name (optional with credentials JSON)<input autoComplete="off" value={form.key_name} onChange={e=>setForm({...form,key_name:e.target.value})} placeholder="organizations/.../apiKeys/..." className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <label className="block text-sm">Private key<textarea autoComplete="off" required value={form.private_key} onChange={e=>setForm({...form,private_key:e.target.value})} rows={4} placeholder="Paste the original Coinbase private key or credentials JSON" className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <button disabled={busy} className="rounded bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-50">{busy ? "Verifying…" : "Verify & save Coinbase"}</button>
        {saved.coinbase?.saved && <button type="button" disabled={busy} onClick={disconnect} className="ml-3 rounded border border-red-700 px-4 py-2 text-red-300 disabled:opacity-50">Disconnect</button>}
      </form>
      <p className="mt-4 text-xs text-slate-400">View permission is enough for connection verification. Automatic Coinbase trading requires View + Trade with Transfer disabled and an explicit Start in the bot. Saving a key never starts orders. Never share API keys in chat or diagnostic exports.</p>
    </div>
    <p className="text-xs text-slate-400">Broker names marked “Adapter pending” are not available for automated trading yet. Selecting a broker does not imply that live trading is supported.</p>
  </section>;
}
