import React, { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";

const BROKERS = [
  ["coinbase", "Coinbase Advanced", "https://advanced.coinbase.com/", "API integration"],
  ["pocketoption", "Pocket Option", "https://pocketoption.com/", "Extension integration"],
  ["kraken", "Kraken", "https://www.kraken.com/", "Adapter pending"],
  ["ibkr", "Interactive Brokers", "https://www.interactivebrokers.com/", "Gateway adapter pending"],
  ["alpaca", "Alpaca", "https://alpaca.markets/", "Live adapter pending"],
  ["alpaca_paper", "Alpaca Paper", "https://app.alpaca.markets/", "Paper account connection"],
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
  const [alpacaForm,setAlpacaForm] = useState({key_id:"",secret_key:""});
  const [alpacaBusy,setAlpacaBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
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
  async function saveAlpaca(event) {
    event.preventDefault();setAlpacaBusy(true);setError("");setNotice("");
    try {
      await api.put("/api/v1/broker-connections/alpaca-paper",alpacaForm);
      setAlpacaForm({key_id:"",secret_key:""});
      setNotice("Alpaca Paper verified and saved. This connection cannot place live trades.");
      await load();
    } catch(e) {setError("Alpaca Paper connection failed: "+errMsg(e));}
    finally {setAlpacaBusy(false);}
  }
  async function disconnectAlpaca() {
    if (!window.confirm("Disconnect your Alpaca paper account from KAOS?")) return;
    setAlpacaBusy(true);setError("");
    try {
      await api.delete("/api/v1/broker-connections/alpaca-paper");
      setNotice("Alpaca Paper disconnected.");await load();
    } catch(e){setError(errMsg(e));} finally{setAlpacaBusy(false);}
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
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm">API key name<input autoComplete="off" required value={form.key_name} onChange={e=>setForm({...form,key_name:e.target.value})} placeholder="organizations/.../apiKeys/..." className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <label className="block text-sm">Private key<textarea autoComplete="off" required value={form.private_key} onChange={e=>setForm({...form,private_key:e.target.value})} rows={4} placeholder="Paste the original Coinbase key" className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3 text-white" /></label>
        <button disabled={busy} className="rounded bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-50">{busy ? "Verifying…" : "Verify & save Coinbase"}</button>
        {saved.coinbase?.saved && <button type="button" disabled={busy} onClick={disconnect} className="ml-3 rounded border border-red-700 px-4 py-2 text-red-300 disabled:opacity-50">Disconnect</button>}
      </form>
      <p className="mt-4 text-xs text-slate-400">Use View + Trade permissions; disable transfers. Never include keys in diagnostic exports.</p>
    </div>
    <div className="rounded-lg border border-[#D4AF37]/40 bg-[#111] p-5" data-testid="alpaca-paper-connection">
      <h2 className="text-xl font-semibold text-[#D4AF37]">Alpaca Paper Trading</h2>
      <p className="mt-2 text-sm text-slate-400">Connect an Alpaca paper account to view its paper portfolio and order history in KAOS. Use paper API credentials only; live Alpaca keys will not work against the paper endpoint.</p>
      <p className="mt-2 text-xs text-amber-300">This first stage is read-only. Connecting does not authorize AI or manual order submission.</p>
      <form onSubmit={saveAlpaca} className="mt-4 space-y-3">
        <label className="block text-sm">Paper API key ID
          <input autoComplete="off" maxLength={512} className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3"
            value={alpacaForm.key_id} onChange={e=>setAlpacaForm({...alpacaForm,key_id:e.target.value})} required />
        </label>
        <label className="block text-sm">Paper API secret
          <input type="password" autoComplete="off" maxLength={2048} className="mt-1 w-full rounded border border-slate-600 bg-[#080808] p-3"
            value={alpacaForm.secret_key} onChange={e=>setAlpacaForm({...alpacaForm,secret_key:e.target.value})} required />
        </label>
        <button type="submit" disabled={alpacaBusy} className="rounded bg-[#D4AF37] px-4 py-2 font-semibold text-black disabled:opacity-50">{alpacaBusy?"Verifying…":"Verify & save paper account"}</button>
        {saved.alpaca_paper?.saved&&<button type="button" disabled={alpacaBusy} onClick={disconnectAlpaca} className="ml-3 rounded border border-red-700 px-4 py-2 text-red-300">Disconnect</button>}
      </form>
      {saved.alpaca_paper?.verified&&<a href="/dashboard/paper" className="mt-3 inline-block text-sm text-[#D4AF37] underline">Go to Paper Trading</a>}
      <p className="mt-3 text-xs text-slate-500">Credentials are verified on Alpaca's dedicated paper API and encrypted on the KAOS server. Never paste keys into public chat or screenshots.</p>
    </div>
    <p className="text-xs text-slate-400">Broker names marked “Adapter pending” are not available for automated trading yet. Selecting a broker does not imply that live trading is supported.</p>
  </section>;
}
